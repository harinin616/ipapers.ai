import logging
import uuid
from typing import List, Optional
from sqlalchemy.future import select
from sqlalchemy import func, text, update, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone
from sqlalchemy import distinct

from app.models.paper import Paper
from app.models.db_models import DBPaper, DBAuthor, DBCategory, DBUser, DBSession, DBMessage, paper_authors,DBUserFile, DBEmailList, DBUserTopic,DBFolder,paper_categories,paper_authors,DBSharedFolder
from app.models.db_models import DBComment,shared_folder_comments
from app.db.database import get_async_db

from app.services.llm_service import llm_service 
from app.services.extract_info import paper_info_extractor



logger = logging.getLogger(__name__)


class DBService:
    """
    PostgreSQL database service to interact with database
    """
    
    def __init__(self):
        pass
    
    async def get_user_id_by_email(self, email: str) -> Optional[int]:
        """
        Get user ID by email address
        Returns user_id if found, None if not found
        """
        if not email:
            logger.warning("Attempted to get user ID with empty email")
            return None
            
        async for db in get_async_db():
            try:
                result = await db.execute(
                    select(DBUser.id).where(DBUser.email == email)
                )
                user_id = result.scalar_one_or_none()
                
                if user_id is None:
                    logger.info(f"User with email {email} not found")
                    return None
                
                return user_id
                
            except SQLAlchemyError as e:
                logger.error(f"Database error when getting user ID for email {email}: {str(e)}")
                return None
            except Exception as e:
                logger.error(f"Unexpected error when getting user ID for email {email}: {str(e)}", exc_info=True)
                return None
        
        return None

    
    async def add_user(self,user_id: uuid.UUID, name: str, email: str) -> bool:
        """
        Add user to database, check if email already exists first
        """
        if not name or not email:
            logger.warning("Attempted to add user with empty name or email")
            return False
            
        async for db in get_async_db():
            try:
                # Check if user with this email already exists
                result = await db.execute(
                    select(DBUser).where(DBUser.email == email)
                )
                existing_user = result.scalars().first()
                
                if existing_user:
                    return True
                
                # Create new user
                new_user = DBUser(
                    id=user_id,
                    name=name,
                    email=email,
                )
                
                db.add(new_user)
                await db.commit()
                
                logger.info(f"Successfully added new user: {name} with email: {email}")
                return True
                
            except SQLAlchemyError as e:
                await db.rollback()
                logger.error(f"Database error when adding user {email}: {str(e)}")
                return False
            except Exception as e:
                await db.rollback()
                logger.error(f"Unexpected error when adding user {email}: {str(e)}", exc_info=True)
                return False
        
        return False
    
    async def add_papers(self, papers: List[Paper]) -> List[str]:
        """
        Add papers list to the database and generate+store embeddings.
        """
        if not papers:
            return []

        added_ids: List[str] = []

        async for db in get_async_db():  # db: AsyncSession
            try:
                # 1. 查已有的 paper_id，过滤掉已有的
                incoming_ids = [p.paper_id for p in papers]
                result = await db.execute(
                    select(DBPaper.paper_id).where(DBPaper.paper_id.in_(incoming_ids))
                )
                existing_ids = set(result.scalars().all())

                papers_to_add = [p for p in papers if p.paper_id not in existing_ids]
                if not papers_to_add:
                    logger.info("All papers already exist, skipping insert.")
                    return []

                logger.info(f"{len(papers_to_add)} new papers to insert "
                            f"(skipped {len(papers) - len(papers_to_add)})")

                # 2. 批量生成 embeddings
                texts = [f"{p.title}\n\n{p.abstract}" for p in papers_to_add]
                embeddings = await llm_service.get_embeddings(texts)
                if embeddings is None:
                    logger.error("Embedding service returned None, "
                                 "skipping embeddings for this batch.")
                    embeddings = [None] * len(papers_to_add)

                # 3. 预取所有 author/category 名并 sync 到数据库
                all_authors = {a for p in papers_to_add for a in p.authors}
                all_cats    = {c for p in papers_to_add for c in p.categories}

                existing_authors = {}
                if all_authors:
                    res = await db.execute(select(DBAuthor).where(DBAuthor.name.in_(all_authors)))
                    for a in res.scalars().all():
                        existing_authors[a.name] = a
                to_create = all_authors - existing_authors.keys()
                if to_create:
                    db.add_all([DBAuthor(name=n) for n in to_create])
                    await db.flush()
                    res = await db.execute(select(DBAuthor).where(DBAuthor.name.in_(all_authors)))
                    for a in res.scalars().all():
                        existing_authors[a.name] = a

                existing_cats = {}
                if all_cats:
                    res = await db.execute(select(DBCategory).where(DBCategory.name.in_(all_cats)))
                    for c in res.scalars().all():
                        existing_cats[c.name] = c
                to_create = all_cats - existing_cats.keys()
                if to_create:
                    db.add_all([DBCategory(name=n) for n in to_create])
                    await db.flush()
                    res = await db.execute(select(DBCategory).where(DBCategory.name.in_(all_cats)))
                    for c in res.scalars().all():
                        existing_cats[c.name] = c

                # 4. 插入 papers + embedding + 关联表
                for p, emb in zip(papers_to_add, embeddings):
                    db_p = DBPaper(
                        paper_id      = p.paper_id,
                        title         = p.title,
                        abstract      = p.abstract,
                        pdf_url       = p.pdf_url.replace("http://", "https://"),
                        published_date= p.published_date,
                        updated_date  = p.updated_date,
                        click_count   = 0,
                        embedding     = emb   # ← 直接存 embedding 列
                    )
                    # 4.1 关联 categories
                    for cat in p.categories:
                        db_p.categories.append(existing_cats[cat])

                    db.add(db_p)
                    await db.flush()  # 以便有 paper_id

                    # 4.2 关联 authors（保留顺序）
                    for order, name in enumerate(p.authors):
                        await db.execute(
                            text("""
                              INSERT INTO paper_authors (paper_id, author, author_order)
                              VALUES (:pid, :auth, :ord)
                              ON CONFLICT (paper_id, author) DO UPDATE
                              SET author_order = EXCLUDED.author_order
                            """),
                            {"pid": p.paper_id, "auth": name, "ord": order}
                        )
                    added_ids.append(p.paper_id)

                # 5. 提交事务
                await db.commit()
                logger.info(f"Inserted {len(added_ids)} papers with embeddings.")

            except Exception:
                await db.rollback()
                logger.exception("Error adding papers")
                raise
        return added_ids

    async def get_all_papers(self) -> List[Paper]:
        """
        Retrieve *all* papers from the database.
        """
        papers: List[Paper] = []
        async for db in get_async_db():
            # Select everything
            result = await db.execute(
                select(DBPaper)
                .options(
                    selectinload(DBPaper.authors),
                    selectinload(DBPaper.categories)
                )
                # no limit or offset → fetch all
            )
            db_papers = result.scalars().all()
            for db_paper in db_papers:
                papers.append(Paper(
                    paper_id=db_paper.paper_id,
                    title=db_paper.title,
                    authors=[a.name for a in db_paper.authors],
                    abstract=db_paper.abstract,
                    categories=[c.name for c in db_paper.categories],
                    pdf_url=db_paper.pdf_url.replace("http://", "https://"),
                    published_date=db_paper.published_date,
                    updated_date=db_paper.updated_date
                ))
        return papers
        
    async def get_paper_by_id(self, paper_id: str) -> Optional[Paper]:
        """
        get paper Object by paper_id
        """
        logger.info(f"Looking up paper in database with ID: {paper_id}")
        
        if not paper_id:
            logger.warning("Attempted to get paper with empty ID")
            return None
            
        try:
            async for db in get_async_db():
                try:
                    result = await db.execute(
                        select(DBPaper)
                        .options(
                            selectinload(DBPaper.authors),
                            selectinload(DBPaper.categories)
                        )
                        .where(DBPaper.paper_id == paper_id)
                    )
                    db_paper = result.scalars().first()
                    
                    if not db_paper:
                        logger.info(f"Paper with ID {paper_id} not found in database")
                        return None
                    
                    # Convert to API model - authors will now be in correct order due to order_by in relationship
                    paper = Paper(
                        paper_id=db_paper.paper_id,
                        title=db_paper.title,
                        authors=[author.name for author in db_paper.authors],
                        abstract=db_paper.abstract,
                        categories=[category.name for category in db_paper.categories],
                        pdf_url=db_paper.pdf_url.replace("http://", "https://"),
                        published_date=db_paper.published_date,
                        updated_date=db_paper.updated_date
                    )
                    
                    logger.info(f"success get paper: {paper.title} (ID: {paper.paper_id})")
                    return paper
                    
                except SQLAlchemyError as e:
                    logger.error(f"Database error when getting paper by ID {paper_id}: {str(e)}")
                    return None
        except Exception as e:
            logger.error(f"Unexpected error when getting paper by ID {paper_id}: {str(e)}", exc_info=True)
            return None
        
        logger.warning(f"Paper lookup completed with no result for ID: {paper_id}")
        return None

    async def get_papers_by_ids(self, paper_ids: List[str]) -> List[Paper]:
        async for db in get_async_db():
            stmt = (
                select(
                    DBPaper.paper_id,
                    DBPaper.title,
                    DBPaper.abstract,
                    DBPaper.pdf_url,
                    DBPaper.published_date,
                    DBPaper.updated_date,
                    # 把作者名聚成数组
                    func.coalesce(
                        func.array_agg(DBAuthor.name.op('ORDER BY')(paper_authors.c.author_order))
                        .filter(paper_authors.c.paper_id == DBPaper.paper_id),
                        []
                    ).label("author_names"),
                    # 把分类名聚成数组
                    func.coalesce(
                        func.array_agg(distinct(DBCategory.name))
                        .filter(paper_categories.c.paper_id == DBPaper.paper_id),
                        []
                    ).label("category_names"),
                )
                .outerjoin(paper_authors, paper_authors.c.paper_id == DBPaper.paper_id)
                .outerjoin(DBAuthor, DBAuthor.name == paper_authors.c.author)
                .outerjoin(paper_categories, paper_categories.c.paper_id == DBPaper.paper_id)
                .outerjoin(DBCategory, DBCategory.name == paper_categories.c.category)
                .where(DBPaper.paper_id.in_(paper_ids))
                .group_by(
                    DBPaper.paper_id,
                    DBPaper.title,
                    DBPaper.abstract,
                    DBPaper.pdf_url,
                    DBPaper.published_date,
                    DBPaper.updated_date,
                )
            )
            result = await db.execute(stmt)
            rows = result.all()

        papers: List[Paper] = []
        for row in rows:
            papers.append(
                Paper(
                    paper_id=row.paper_id,
                    title=row.title,
                    authors=row.author_names,
                    abstract=row.abstract,
                    categories=row.category_names,
                    pdf_url=row.pdf_url.replace("http://", "https://"),
                    published_date=row.published_date,
                    updated_date=row.updated_date
                )
            )
        return papers


    
    
    async def get_recent_papers(self, limit: int = 30, keyword: str = None, offset: int = 0) -> List[Paper]:
        """
        get recent papers from database
        """
    
        papers = []
        async for db in get_async_db():
            # Build base query
            query = select(DBPaper).options(
                selectinload(DBPaper.authors),
                selectinload(DBPaper.categories)
            ).order_by(DBPaper.published_date.desc()).limit(limit).offset(offset)
            
            # Add keyword filter if provided
            if keyword:
                query = query.where(DBPaper.title.ilike(f"%{keyword}%"))
            
            result = await db.execute(query)
            db_papers = result.scalars().all()
            
            for db_paper in db_papers:
                papers.append(Paper(
                    paper_id=db_paper.paper_id,
                    title=db_paper.title,
                    authors=[author.name for author in db_paper.authors],
                    abstract=db_paper.abstract,
                    categories=[category.name for category in db_paper.categories],
                    pdf_url=db_paper.pdf_url.replace("http://", "https://"),
                    published_date=db_paper.published_date,
                    updated_date=db_paper.updated_date,
                    platform=paper_info_extractor.extract_platform(db_paper.paper_id)
                ))
        
        return papers
    
    
    async def count_papers(self) -> int:
        """
        count total papers in database
        """
        async for db in get_async_db():
            result = await db.execute(select(func.count()).select_from(DBPaper))
            count = result.scalar_one()
            return count
        return 0
    
    async def click_paper(self, paper_id: str) -> bool:
        """
        Increment click count for a paper by 1 in a transaction
        """
        if not paper_id:
            logger.warning("Attempted to click paper with empty ID")
            return False
        
        async for db in get_async_db():
            try:
                result = await db.execute(
                    update(DBPaper)
                    .where(DBPaper.paper_id == paper_id)
                    .values(click_count=DBPaper.click_count + 1)
                )
                
                if result.rowcount == 0:
                    logger.warning(f"Paper {paper_id} not found for click recording")
                    return False
                
                await db.commit()
                logger.info(f"Successfully recorded click for paper ID: {paper_id}")
                return True
                
            except SQLAlchemyError as e:
                await db.rollback()
                logger.error(f"Database error when recording click for paper ID {paper_id}: {str(e)}")
                return False
            except Exception as e:
                await db.rollback()
                logger.error(f"Unexpected error when recording click for paper ID {paper_id}: {str(e)}", exc_info=True)
                return False
        
        return False
    
    async def get_paper_click_count(self, paper_id: str) -> Optional[int]:
        """
        Get the current click count for a paper
        """
        if not paper_id:
            logger.warning("Attempted to get click count for paper with empty ID")
            return None
            
        async for db in get_async_db():
            try:
                result = await db.execute(
                    select(DBPaper.click_count)
                    .where(DBPaper.paper_id == paper_id)
                )
                click_count = result.scalar_one_or_none()
                
                if click_count is None:
                    logger.info(f"Paper with ID {paper_id} not found when getting click count")
                    return None
                
                return click_count
                
            except SQLAlchemyError as e:
                logger.error(f"Database error when getting click count for paper ID {paper_id}: {str(e)}")
                return None
            except Exception as e:
                logger.error(f"Unexpected error when getting click count for paper ID {paper_id}: {str(e)}", exc_info=True)
                return None
        
        return None

    async def add_session(self, session_id: str, user_id: uuid.UUID, session_time: datetime, title: str = "untitled") -> bool:
        """
        Create a new chat session for a user
        """
        if not session_id or not user_id:
            logger.warning("Attempted to create session with empty session_id or user_id")
            return False
            
        async for db in get_async_db():
            try:
                # Check if session with this ID already exists
                result = await db.execute(
                    select(DBSession).where(DBSession.session_id == session_id)
                )
                existing_session = result.scalars().first()
                
                if existing_session:
                    logger.warning(f"Session with ID {session_id} already exists")
                    return False
                
                # Check if user exists
                result = await db.execute(
                    select(DBUser).where(DBUser.id == user_id)
                )
                user = result.scalars().first()
                
                if not user:
                    logger.warning(f"User with ID {user_id} not found")
                    return False
                
                # Create new session with specified time and title
                new_session = DBSession(
                    session_id=session_id,
                    user_id=user_id,
                    title=title,
                    created_at=session_time,
                    last_message_at=session_time
                )
                
                db.add(new_session)
                await db.commit()
                
                logger.info(f"Successfully created new session: {session_id} for user: {user_id} with title: {title} at {session_time}")
                return True
                
            except SQLAlchemyError as e:
                await db.rollback()
                logger.error(f"Database error when creating session {session_id}: {str(e)}")
                return False
            except Exception as e:
                await db.rollback()
                logger.error(f"Unexpected error when creating session {session_id}: {str(e)}", exc_info=True)
                return False
        
        return False

    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a chat session and all its messages
        """
        if not session_id:
            logger.warning("the session id is empty")
            return False
            
        async for db in get_async_db():
            try:
                # Check if session exists
                result = await db.execute(
                    select(DBSession).where(DBSession.session_id == session_id)
                )
                session = result.scalars().first()
                
                if not session:
                    logger.warning(f"Session with ID {session_id} not found")
                    return False
                
                # First delete all messages associated with this session
                await db.execute(
                    delete(DBMessage).where(DBMessage.session_id == session_id)
                )
                
                # Then delete the session
                await db.execute(
                    delete(DBSession).where(DBSession.session_id == session_id)
                )
                
                await db.commit()
                
                logger.info(f"Successfully deleted session: {session_id} and all messages")
                return True
                
            except SQLAlchemyError as e:
                await db.rollback()
                logger.error(f"Database error when deleting session {session_id}: {str(e)}")
                return False
            except Exception as e:
                await db.rollback()
                logger.error(f"Unexpected error when deleting session {session_id}: {str(e)}", exc_info=True)
                return False
        
        return False

    async def add_message(self, session_id: str, content: str, role: str, message_time: datetime) -> bool:
        """
        Add a new message to a chat session
        """
        if not session_id:
            logger.info("empty session id")
            return False
            
        async for db in get_async_db():
            try:
                result = await db.execute(
                    select(DBSession).where(DBSession.session_id == session_id)
                )
                session = result.scalars().first()
                
                if not session:
                    logger.info(f"Session {session_id} not found")
                    return False
                
                new_message = DBMessage(
                    session_id=session_id,
                    content=content,
                    role=role,
                    created_at=message_time
                )
                
                db.add(new_message)
                
                await db.execute(
                    update(DBSession)
                    .where(DBSession.session_id == session_id)
                    .values(last_message_at=message_time)
                )
                
                await db.commit()
                
                logger.info(f"Successfully added message to session: {session_id}, role: {role}, time: {message_time}")
                return True
                
            except SQLAlchemyError as e:
                await db.rollback()
                logger.error(f"Database error when adding message to session {session_id}: {str(e)}")
                return False
            except Exception as e:
                await db.rollback()
                logger.error(f"Unexpected error when adding message to session {session_id}: {str(e)}", exc_info=True)
                return False
        
        return False

    async def update_session_title(self, session_id: str, title: str) -> bool:
        """
        Update the title of a chat session
        """
        if not session_id:
            logger.info("empty session id")
            return False
            
        async for db in get_async_db():
            try:
                result = await db.execute(
                    select(DBSession).where(DBSession.session_id == session_id)
                )
                session = result.scalars().first()
                
                if not session:
                    logger.info(f"Session {session_id} not found")
                    return False
                
                await db.execute(
                    update(DBSession)
                    .where(DBSession.session_id == session_id)
                    .values(title=title)
                )
                
                await db.commit()
                
                logger.info(f"Successfully updated session title: {session_id} -> {title}")
                return True
                
            except SQLAlchemyError as e:
                await db.rollback()
                logger.error(f"Database error when updating session title {session_id}: {str(e)}")
                return False
            except Exception as e:
                await db.rollback()
                logger.error(f"Unexpected error when updating session title {session_id}: {str(e)}", exc_info=True)
                return False
        
        return False

    async def get_sessions_by_user_id(self, user_id: uuid.UUID) -> List[dict]:
        """
        Get all sessions for a specific user
        """
        if not user_id:
            logger.info("empty user_id")
            return []
            
        async for db in get_async_db():
            try:
                result = await db.execute(
                    select(DBSession)
                    .where(DBSession.user_id == user_id)
                    .order_by(DBSession.last_message_at.desc())
                )
                sessions = result.scalars().all()
                
                session_list = []
                for session in sessions:
                    session_list.append({
                        "session_id": session.session_id,
                        "title": session.title,
                        "created_at": session.created_at.isoformat() if session.created_at else None,
                        "last_message_at": session.last_message_at.isoformat() if session.last_message_at else None
                    })
                
                logger.info(f"get {len(session_list)} sessions for user {user_id}")
                return session_list
                
            except SQLAlchemyError as e:
                logger.error(f"Database error when getting sessions for user {user_id}: {str(e)}")
                return []
            except Exception as e:
                logger.error(f"Unexpected error when getting sessions for user {user_id}: {str(e)}", exc_info=True)
                return []
        
        return []

    async def get_messages_by_session_id(self, session_id: str) -> List[dict]:
        """
        Get all messages for a session
        """
        if not session_id:
            logger.warning("empty session_id")
            return []
            
        async for db in get_async_db():
            try:
                session_result = await db.execute(
                    select(DBSession).where(DBSession.session_id == session_id)
                )
                session = session_result.scalars().first()
                
                if not session:
                    logger.info(f"Session {session_id} not found")
                    return []
                
                # Get all messages for this session
                result = await db.execute(
                    select(DBMessage)
                    .where(DBMessage.session_id == session_id)
                    .order_by(DBMessage.created_at.asc())
                )
                messages = result.scalars().all()
                
                message_list = []
                for message in messages:
                    message_list.append({
                        "message_id": message.message_id,
                        "content": message.content,
                        "role": message.role,
                        "created_at": message.created_at.isoformat() if message.created_at else None
                    })
                
                logger.info(f"get    {len(message_list)} messages for session {session_id}")
                return message_list
                
            except SQLAlchemyError as e:
                logger.error(f"Database error when getting messages for session {session_id}: {str(e)}")
                return []
            except Exception as e:
                logger.error(f"Unexpected error when getting messages for session {session_id}: {str(e)}", exc_info=True)
                return []
        
        return []
    
    async def get_files_by_user_id(self, user_id: uuid.UUID) -> List[dict]:
        """
        拉取某用户 *所有文件*（跨文件夹），按 added_at DESC。
        返回字段：
            file_path (预留空) | filename | paper_id | paper_URL | added_at | selected
        """
        if not user_id:
            logger.info("empty user_id")
            return []

        async for db in get_async_db():
            try:
                # 1) 通过 folders JOIN user_files → 预加载 paper
                stmt = (
                    select(DBUserFile)
                    .join(DBFolder, DBFolder.id == DBUserFile.folder_id)
                    .where(DBFolder.user_id == user_id)
                    .options(selectinload(DBUserFile.paper))
                    .order_by(DBUserFile.added_at.desc())
                )
                result = await db.execute(stmt)
                user_files: List[DBUserFile] = result.scalars().all()

                # 2) 组装返回列表
                file_list: List[dict] = []
                for uf in user_files:
                    paper = uf.paper         # 已通过 relationship 预加载
                    file_list.append({
                        "file_path": "",     # 你之前保留的字段
                        "filename":  paper.title,
                        "paper_id":  uf.paper_id,
                        "paper_URL": (
                            paper.pdf_url.replace("http://", "https://")
                            if paper.pdf_url else None
                        ),
                        "added_at": (
                            uf.added_at.isoformat()
                            if isinstance(uf.added_at, datetime) else None
                        ),
                        "selected": uf.selected if uf.selected is not None else False
                    })

                logger.info(f"get {len(file_list)} files for user {user_id}")
                return file_list

            except SQLAlchemyError as e:
                logger.error(
                    f"Database error when getting files for user {user_id}: {e}"
                )
                return []
            except Exception as e:
                logger.error(
                    f"Unexpected error when getting files for user {user_id}",
                    exc_info=True
                )
                return []

        # 数据库连接意外中断
        return []
            
    async def add_file_to_user(self, user_id: int, paper_id: str) -> bool:
        """
        把 paper 放进用户的“默认文件夹”：
        1. 找到 user→folders.name=='default'；若不存在就创建
        2. 在该 folder 内插入 (folder_id, paper_id)
        True  = 新增成功 / 已存在
        False = 参数错误或数据库异常
        """
        if not user_id or not paper_id:
            logger.warning("invalid user_id or paper_id")
            return False

        async for db in get_async_db():
            try:
                # -------- 1) 校验用户 & 论文 --------
                user = (await db.execute(
                    select(DBUser).where(DBUser.user_id == user_id))
                ).scalars().first()
                if not user:
                    logger.info(f"user {user_id} not found")
                    return False

                paper = (await db.execute(
                    select(DBPaper).where(DBPaper.paper_id == paper_id))
                ).scalars().first()
                if not paper:
                    logger.info(f"paper {paper_id} not found")
                    return False

                # -------- 2) 拿 / 建 default folder --------
                folder = (await db.execute(
                    select(DBFolder)
                    .where(DBFolder.user_id == user_id, DBFolder.name == "default"))
                ).scalars().first()

                if not folder:
                    folder = DBFolder(user_id=user_id, name="default")
                    db.add(folder)
                    await db.flush()          # 获得 folder.id

                # -------- 3) 插入 (folder_id, paper_id) --------
                entry = DBUserFile(folder_id=folder.id, paper_id=paper_id)
                db.add(entry)
                await db.commit()
                return True

            except IntegrityError:
                # 同一 folder 已有这篇 paper，无需重复
                await db.rollback()
                logger.info(
                    f"paper {paper_id} already in user {user_id}'s default folder"
                )
                return True

            except SQLAlchemyError as e:
                await db.rollback()
                logger.error(f"DB error adding file to default folder: {e}")
                return False
    async def add_file_to_folder(self,folder_id: int, paper_id: str) -> bool:
        # 检查 folder 属于 user
        async for db in get_async_db():
            folder = (await db.execute(
                select(DBFolder)
                  .where(DBFolder.id==folder_id)
            )).scalars().first()
            if not folder:
                return False
            entry = DBUserFile(folder_id=folder_id, paper_id=paper_id)
            db.add(entry)
            try:
                await db.commit()
                return True
            except IntegrityError:
                await db.rollback()
                return True
            except SQLAlchemyError:
                await db.rollback()
                return False
        return False

    async def remove_file_from_user(self, user_id: int, paper_id: str) -> bool:
        """
        删除 (paper_id) 在用户任意文件夹中的记录。
        · 找得到即删，可能删除多条（不同文件夹副本）
        · 若完全找不到，再尝试只删 default 文件夹里的记录
        """
        if not (user_id and paper_id):
            logger.warning("invalid user_id or paper_id")
            return False

        async for db in get_async_db():
            try:
                # ---------- 1. 删除所有匹配行 ----------
                # JOIN folders → 保证 folder 属于当前 user
                stmt = (
                    delete(DBUserFile)
                    .where(DBUserFile.paper_id == paper_id)
                    .where(
                        DBUserFile.folder_id.in_(
                            select(DBFolder.id).where(DBFolder.user_id == user_id)
                        )
                    )
                )
                result = await db.execute(stmt)
                await db.commit()

                if result.rowcount and result.rowcount > 0:
                    logger.info(
                        f"removed paper {paper_id} ({result.rowcount} rows) "
                        f"from user {user_id}'s folders"
                    )
                    return True

                # ---------- 2. 兼容旧数据：default 文件夹 ----------
                default_id = (await db.execute(
                    select(DBFolder.id)
                    .where(DBFolder.user_id == user_id,
                        DBFolder.name == "default")
                )).scalar_one_or_none()

                if default_id is None:
                    logger.info(f"file {paper_id} not found for user {user_id}")
                    return False

                stmt_default = (
                    delete(DBUserFile)
                    .where(DBUserFile.folder_id == default_id,
                        DBUserFile.paper_id == paper_id)
                )
                res2 = await db.execute(stmt_default)
                await db.commit()

                if res2.rowcount and res2.rowcount > 0:
                    logger.info(
                        f"removed paper {paper_id} from user {user_id}'s default folder"
                    )
                    return True

                logger.info(f"file {paper_id} not found for user {user_id}")
                return False

            except SQLAlchemyError as e:
                await db.rollback()
                logger.error(
                    f"DB error deleting paper {paper_id} for user {user_id}: {e}"
                )
                return False

    async def remove_file_from_folder(
        self,
        user_id: int,
        folder_id: int,
        paper_id: str
    ) -> bool:
        """
        从用户的指定文件夹移除一篇 paper。
        返回 True 表示已删除，False 表示未找到或出错。
        """
        if not user_id or not folder_id or not paper_id:
            logger.warning("invalid user_id, folder_id or paper_id")
            return False

        async for db in get_async_db():
            try:
                # 1) 验证这个 folder 确实属于当前 user
                folder = (
                    await db.execute(
                        select(DBFolder)
                        .where(DBFolder.id == folder_id, DBFolder.user_id == user_id)
                    )
                ).scalars().first()
                if not folder:
                    logger.info(f"folder {folder_id} not found for user {user_id}")
                    return False

                # 2) 删除关联表里的记录
                stmt = (
                    delete(DBUserFile)
                    .where(
                        DBUserFile.folder_id == folder_id,
                        DBUserFile.paper_id  == paper_id
                    )
                )
                result = await db.execute(stmt)
                await db.commit()

                if result.rowcount and result.rowcount > 0:
                    logger.info(f"removed paper {paper_id} from folder {folder_id}")
                    return True
                else:
                    logger.info(f"paper {paper_id} not in folder {folder_id}")
                    return False

            except SQLAlchemyError as e:
                await db.rollback()
                logger.error(f"DB error removing paper from folder {folder_id}: {e}")
                return False

        return False



    # ============= EMAIL LIST MANAGEMENT =============
    
    async def add_email_to_list(self, email: str) -> bool:
        """
        Add email to the subscription list
        Returns True if successful (either newly added or already exists), False otherwise
        """
        if not email or not email.strip():
            logger.warning("Attempted to add empty email to subscription list")
            return False
            
        email = email.strip().lower()  # Normalize email
        
        # Basic email validation
        if '@' not in email or '.' not in email.split('@')[-1]:
            logger.warning(f"Invalid email format: {email}")
            return False
            
        async for db in get_async_db():
            try:
                # Check if email already exists
                result = await db.execute(
                    select(DBEmailList).where(DBEmailList.email == email)
                )
                existing_email = result.scalars().first()
                
                if existing_email:
                    logger.info(f"Email {email} already in subscription list")
                    return True
                
                # Add new email
                new_email = DBEmailList(email=email)
                db.add(new_email)
                await db.commit()
                
                logger.info(f"Successfully added email {email} to subscription list")
                return True
                
            except SQLAlchemyError as e:
                await db.rollback()
                logger.error(f"Database error when adding email {email}: {str(e)}")
                return False
            except Exception as e:
                await db.rollback()
                logger.error(f"Unexpected error when adding email {email}: {str(e)}", exc_info=True)
                return False
        
        return False

    async def create_user_by_uuid(self, user_id: uuid.UUID) -> DBUser | None:
        if not user_id:
            logger.warning("create_user_by_uuid called with empty user_id")
            return None

        async for db in get_async_db():
            try:
                # 检查用户是否已存在
                existing_user = await db.scalar(
                    select(DBUser.id).where(DBUser.id == user_id)
                )
                if existing_user:
                    logger.info(f"User {user_id} already exists")
                    return existing_user  # 用户已存在，返回现有用户

                # 创建新用户
                new_user = DBUser(id=user_id)
                db.add(new_user)
                await db.commit()
                await db.refresh(new_user)  # 刷新以获取最新数据
                logger.info(f"Created new user with ID {user_id}")
                return new_user

            except SQLAlchemyError as e:
                await db.rollback()
                logger.error(f"Database error when creating user {user_id}: {str(e)}")
                return None
            except Exception as e:
                await db.rollback()
                logger.error(f"Unexpected error when creating user {user_id}: {str(e)}", exc_info=True)
                return None

        return None
    
    async def add_topic_to_user(self, user_id: uuid.UUID, topic: str) -> bool:
        """
        给用户添加一个 topic；若已存在则直接返回 True。
        """
        if not user_id or not topic:
            logger.warning("invalid user_id or topic")
            return False

        async for db in get_async_db():
            try:
                # 确认用户存在
                await self.create_user_by_uuid(user_id)

                # 若已存在该 (user_id, topic) 组合，直接返回 True
                exists_stmt = select(DBUserTopic).where(
                    DBUserTopic.user_id == user_id,
                    DBUserTopic.topic   == topic
                )
                if await db.scalar(exists_stmt):
                    logger.info(f"topic '{topic}' already linked to user {user_id}")
                    return True

                # 插入
                db.add(DBUserTopic(user_id=user_id, topic=topic))
                await db.commit()
                logger.info(f"added topic '{topic}' to user {user_id}")
                return True

            except SQLAlchemyError as e:
                await db.rollback()
                logger.error(f"DB error adding topic '{topic}' to user {user_id}: {e}")
                return False

        return False
    async def get_topics_by_user(self, user_id: uuid.UUID) -> list[str]:
        """
        返回用户所有 topic 字符串列表（升序）。
        """
        if not user_id:
            return []

        async for db in get_async_db():
            rows = await db.execute(
                select(DBUserTopic.topic)
                .where(DBUserTopic.user_id == user_id)
                .order_by(DBUserTopic.topic.asc())
            )
            return rows.scalars().all()

        return []

    async def remove_topic_from_user(self, user_id: uuid.UUID, topic: str) -> bool:
        """
        删除用户的指定 topic；若不存在返回 False。
        """
        if not user_id or not topic:
            logger.warning("invalid user_id or topic")
            return False

        async for db in get_async_db():
            try:
                stmt = (
                    delete(DBUserTopic)
                    .where(DBUserTopic.user_id == user_id,
                           DBUserTopic.topic   == topic)
                )
                result = await db.execute(stmt)
                await db.commit()

                if result.rowcount and result.rowcount > 0:
                    logger.info(f"removed topic '{topic}' from user {user_id}")
                    return True
                else:
                    logger.info(f"topic '{topic}' not found for user {user_id}")
                    return False

            except SQLAlchemyError as e:
                await db.rollback()
                logger.error(f"DB error deleting topic '{topic}' for user {user_id}: {e}")
                return False

        return False
    async def remove_email_from_list(self, email: str) -> bool:
        """
        Remove email from the subscription list
        Returns True if successfully removed, False if not found or error
        """
        if not email or not email.strip():
            logger.warning("Attempted to remove empty email from subscription list")
            return False
            
        email = email.strip().lower()  # Normalize email
        
        async for db in get_async_db():
            try:
                # Execute DELETE
                result = await db.execute(
                    delete(DBEmailList).where(DBEmailList.email == email)
                )
                await db.commit()
                
                if result.rowcount and result.rowcount > 0:
                    logger.info(f"Successfully removed email {email} from subscription list")
                    return True
                else:
                    logger.info(f"Email {email} not found in subscription list")
                    return False
                    
            except SQLAlchemyError as e:
                await db.rollback()
                logger.error(f"Database error when removing email {email}: {str(e)}")
                return False
            except Exception as e:
                await db.rollback()
                logger.error(f"Unexpected error when removing email {email}: {str(e)}", exc_info=True)
                return False
        
        return False
    
    async def check_email_in_list(self, email: str) -> bool:
        """
        Check if email exists in the subscription list
        Returns True if email is subscribed, False otherwise
        """
        if not email or not email.strip():
            return False
            
        email = email.strip().lower()  # Normalize email
        
        async for db in get_async_db():
            try:
                result = await db.execute(
                    select(DBEmailList).where(DBEmailList.email == email)
                )
                email_record = result.scalars().first()
                return email_record is not None
                
            except SQLAlchemyError as e:
                logger.error(f"Database error when checking email {email}: {str(e)}")
                return False
            except Exception as e:
                logger.error(f"Unexpected error when checking email {email}: {str(e)}", exc_info=True)
                return False
        
        return False
    
    async def get_all_subscription_emails(self) -> List[str]:
        """
        Get all emails from the subscription list
        Returns list of email strings
        """
        async for db in get_async_db():
            try:
                result = await db.execute(
                    select(DBEmailList.email)
                )
                emails = result.scalars().all()
                
                logger.info(f"Retrieved {len(emails)} emails from subscription list")
                return list(emails)
                
            except SQLAlchemyError as e:
                logger.error(f"Database error when getting subscription emails: {str(e)}")
                return []
            except Exception as e:
                logger.error(f"Unexpected error when getting subscription emails: {str(e)}", exc_info=True)
                return []
        
        return []
    
    async def rename_folder(
        self,
        *,
        user_id: int,
        folder_id: int,
        new_name: str,
    ) -> tuple[bool, str]:
        """
        把某用户的 folder 改名为 new_name。
        ▸ 返回 (True, "ok")        —— 成功
        ▸ 返回 (False, reason_str) —— 失败原因
        """
        new_name = (new_name or "").strip()
        if not new_name:
            return False, "empty name"

        async for db in get_async_db():          # type: AsyncSession
            try:
                # ① 取到目标文件夹
                folder = (
                    await db.execute(
                        select(DBFolder).where(
                            DBFolder.id == folder_id,
                            DBFolder.user_id == user_id,
                        )
                    )
                ).scalars().first()

                if folder is None:
                    return False, "folder not found"

                # ② 更新 name
                folder.name = new_name
                if hasattr(folder, "updated_at"):
                    folder.updated_at = datetime.utcnow()

                await db.commit()
                logger.info(
                    "User %s rename folder %s -> %s", user_id, folder_id, new_name
                )
                return True, "ok"

            # ---- 唯一索引冲突：同一用户已有同名文件夹 ----
            except IntegrityError:
                await db.rollback()
                return False, "name already exists"

            # ---- 其它 SQLAlchemy 错误 ----
            except SQLAlchemyError as e:
                await db.rollback()
                logger.error("rename_folder DB error: %s", e)
                return False, "db error"

        # should never reach here
        return False, "unknown error"

    async def get_uuid_by_user_id(self, user_id: int) -> uuid.UUID | None:
        async for db in get_async_db():
            try:
                result = await db.execute(
                    select(DBUser.id).where(DBUser.legacy_user_id == user_id)
                )
                return result.scalar_one_or_none()
            except SQLAlchemyError as e:
                logger.error(f"Database error when getting UUID by user ID {user_id}: {str(e)}")
                return None
            except Exception as e:
                logger.error(f"Unexpected error when getting UUID by user ID {user_id}: {str(e)}", exc_info=True)
                return None

    async def get_folders_with_files(self, user_id: uuid.UUID) -> list[dict]:
        async for db in get_async_db():
            # 预加载 files → paper
            result = await db.execute(
                select(DBFolder)
                .options(
                    selectinload(DBFolder.files)
                    .selectinload(DBUserFile.paper)
                )
                .where(DBFolder.user_id == user_id)
                .order_by(DBFolder.created_at)
            )
            folders: list[DBFolder] = result.scalars().all()

            out = []
            for fld in folders:
                out.append({
                    "id":   fld.id,
                    "name": fld.name,
                    "files": [
                        {
                            "paper_id":  uf.paper_id,
                            "filename":  uf.paper.title,
                            "paper_URL": uf.paper.pdf_url,
                            "added_at":  uf.added_at.isoformat(),
                            "folder_id": fld.id,
                            "selected":  uf.selected if uf.selected is not None else False
                        }
                        for uf in fld.files
                    ]
                })
            return out



    async def create_folder(self, user_id: uuid.UUID, name: str) -> DBFolder | None:
        await self.create_user_by_uuid(user_id)  # 确保用户存在
        async for db in get_async_db():
            try:
                folder = DBFolder(user_id=user_id, name=name)
                db.add(folder)
                await db.commit()
                await db.refresh(folder)
                return folder
            except SQLAlchemyError as e:
                logger.error(
                    "Failed to create folder user=%s name=%s: %s", user_id, name, e
                )
                await db.rollback()
                return None
        return None


    async def delete_folder(self, user_id: uuid.UUID, folder_id: int) -> bool:
        """
        删除指定用户的指定文件夹（连同其下文件一起被级联删除）
        返回 True if deleted, False if not found/not owned.
        """
        async for db in get_async_db():
            try:
                stmt = select(DBFolder).where(
                    DBFolder.id == folder_id,
                    DBFolder.user_id == user_id
                )
                result = await db.execute(stmt)
                folder = result.scalar_one_or_none()
                if not folder:
                    return False
                await db.delete(folder)
                await db.commit()
                return True
            except SQLAlchemyError:
                await db.rollback()
                raise
        return False
    async def get_folder(self, folder_id: int) -> DBFolder | None:
        async for db in get_async_db():
            return await db.get(DBFolder, folder_id)

    async def get_files_by_folder_id(self, folder_id: int) -> list[dict]:
        """
        根据 folder_id 返回该文件夹下所有文件的扁平列表。
        每条记录除了 user_file 信息，还包含 paper 表里的详细字段和 authors 列表。
        """
        async for db in get_async_db():
            try:
                # ① 预加载 paper 及其 authors，避免 N+1
                stmt = (
                    select(DBUserFile)
                    .options(
                        selectinload(DBUserFile.paper)
                            .selectinload(DBPaper.authors)  # 级联加载 authors
                    )
                    .where(DBUserFile.folder_id == folder_id)
                    .order_by(DBUserFile.added_at)
                )
                result = await db.execute(stmt)
                user_files: list[DBUserFile] = result.scalars().all()

                # ② 拼装返回结构
                return [
                    {
                        # 来自 user_files 表
                        "paper_id":       uf.paper_id,
                        "added_at":       uf.added_at.isoformat(),
                        "folder_id":      uf.folder_id,
                        "selected":       bool(uf.selected),

                        # 来自 papers 表
                        "title":          uf.paper.title,
                        "abstract":       uf.paper.abstract,
                        "pdf_url":        uf.paper.pdf_url,
                        "published_date": uf.paper.published_date.isoformat(),
                        "updated_date":   uf.paper.updated_date.isoformat() if uf.paper.updated_date else None,
                        "click_count":    uf.paper.click_count,

                        # 新增：authors 列表
                        "authors":        [author.name for author in uf.paper.authors],
                    }
                    for uf in user_files
                ]

            except SQLAlchemyError as e:
                logger.error("DB error (get_files_by_folder_id): %s", e)
                return []
            except Exception:
                logger.exception("Unexpected error in get_files_by_folder_id")
                return []

    async def create_shared_folder(
        self, *, folder_id: int, owner_id: str, is_public: bool
    ) -> DBSharedFolder:
        async for db in get_async_db():
            # 1) 查询是否已存在相同 folder_id 的记录
            result = await db.execute(
                select(DBSharedFolder).where(DBSharedFolder.folder_id == folder_id)
            )
            existing = result.scalars().first()
            if existing:
                # 已存在，则直接返回，不重复插入
                return existing

            # 2) 不存在时，新增一条
            shared = DBSharedFolder(
                folder_id=folder_id,
                owner_id=owner_id,
                is_public=is_public,
                created_at=datetime.utcnow(),
            )
            db.add(shared)
            await db.commit()
            await db.refresh(shared)
            return shared

        # 如果走不到上面 return，可抛错
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create shared folder"
        )
    
    async def get_shared_folders(self) -> list[dict]:
        """
        返回 [{share_id, folder_name, file_cnt, created_at}, ...]
        """
        async for db in get_async_db():
            try:
                result = await db.execute(
                    select(DBSharedFolder).options(
                        selectinload(DBSharedFolder.folder).selectinload(DBFolder.files)
                    )
                )
                shared: list[DBSharedFolder] = result.scalars().all()

                return [
                    {
                        "id":    sf.id,
                        "folder_id": sf.folder_id,
                        "owner_id":  sf.owner_id,
                        "is_public": sf.is_public,
                        "created_at":  sf.created_at,
                        "folder_name": sf.folder.name if sf.folder else "Unknown",
                        "file_cnt":   len(sf.folder.files) if sf.folder else 0,
                    }
                    for sf in shared
                ]

            except Exception as e:
                logger.error("get_shared_folders failed: %s", e, exc_info=True)
                return []

    async def delete_shared_folder(self, folder_id: int) -> bool:
        """
        删除共享文件夹及其关联数据。
        返回 True if deleted, False if not found.
        """
        async for db in get_async_db():
            try:
                await db.execute(
                    delete(DBSharedFolder).where(DBSharedFolder.folder_id == folder_id)
                )
                await db.commit()
                return True

            except SQLAlchemyError as e:
                await db.rollback()
                logger.error(f"DB error deleting shared folder {folder_id}: {e}")
                return False

    async def update_file_selection(
        self,
        user_id: uuid.UUID,
        paper_id: uuid.UUID,
        selected: bool
    ) -> bool:
        """
        更新用户文件的选中状态。
        返回 True 表示更新成功，False 表示未找到或出错。
        """
        if not user_id or not paper_id:
            logger.warning("invalid user_id or paper_id")
            return False

        async for db in get_async_db():
            try:
                # 1) 验证用户和文件
                user = (await db.execute(
                    select(DBUser).where(DBUser.id == user_id)
                )).scalars().first()
                if not user:
                    logger.info(f"user {user_id} not found")
                    return False

                file = (await db.execute(
                    select(DBUserFile).where(
                        DBUserFile.paper_id == paper_id,
                        DBUserFile.folder.has(user_id=user_id)
                    )
                )).scalars().first()
                if not file:
                    logger.info(f"file {paper_id} not found for user {user_id}")
                    return False

                # 2) 更新选中状态
                file.selected = selected
                await db.commit()
                logger.info(f"Updated selection for paper {paper_id} to {selected} for user {user_id}")
                return True

            except SQLAlchemyError as e:
                await db.rollback()
                logger.error(f"DB error updating selection for paper {paper_id}: {e}")
                return False
            except Exception as e:
                await db.rollback()
                logger.error(f"Unexpected error updating selection for paper {paper_id}: {str(e)}", exc_info=True)
                return False

        return False
    
    async def get_comments_by_folder_id(self, folder_id: int) -> List[dict[str, any]]:
        """
        根据 shared_folder_id 查评论，通过 pivot table。
        """
        try:
            async for db in get_async_db():   # db 是 AsyncSession
                # 1⃣️ 执行异步查询
                result = await db.execute(
                    select(
                        DBComment.id,
                        DBComment.content,
                        DBComment.commenter_name,
                        DBComment.created_at
                    )
                    .join(
                        shared_folder_comments,
                        DBComment.id == shared_folder_comments.c.comment_id
                    )
                    .where(shared_folder_comments.c.shared_folder_id == folder_id)
                    .order_by(DBComment.created_at)  # 不用 asc() 也行
                )

                rows = result.all()
            # 2⃣️ 构造并返回
                return [
                    {
                        "id": row.id,
                        "content": row.content,
                        "commenter_name": row.commenter_name,
                        "created_at": row.created_at.isoformat()
                    }
                    for row in rows
                ]
        except SQLAlchemyError as e:
            logger.error(f"DB error getting comments for folder {folder_id}: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error getting comments for folder {folder_id}: {e}", exc_info=True)
            return []

        # 如果走不到上面 return，说明拿不到 db
        return []

    
    async def add_comment_by_folder_id(
        self,
        user_id: uuid.UUID,
        folder_id: int,
        content: str,
    ) -> Optional[dict[str, any]]:
        """
        添加一条评论到指定的共享文件夹。
        返回:
          {
            "id": int,
            "content": str,
            "commenter_name": str,
            "created_at": str,   # ISO 格式
          }
        如果失败或参数不合法，则返回 None。
        """
        content = content.strip()
        if not content:
            logger.warning("Attempted to add empty comment")
            return None

        async for db in get_async_db():  # type: AsyncSession
            try:
                # 1) 验证 folder 存在
                folder = (
                    await db.execute(
                        select(DBSharedFolder)
                        .where(DBSharedFolder.folder_id == folder_id)
                    )
                ).scalars().first()
                if not folder:
                    logger.warning(f"Shared folder {folder_id} not found")
                    return None

                # 2) 验证用户并获取名字
                user = await db.get(DBUser, user_id)
                commenter_name = user.name if user else ""

                # 3) 创建评论对象
                comment = DBComment(
                    content=content,
                    commenter_id=user_id,
                    commenter_name=commenter_name,
                    created_at=datetime.utcnow()
                )
                # 挂到 folder.comments（pivot table 会自动插入）
                folder.comments.append(comment)
                db.add(comment)

                # 4) 提交并刷新
                await db.commit()
                await db.refresh(comment)

                # 5) 构造返回值
                return {
                    "id": comment.id,
                    "content": comment.content,
                    "commenter_name": comment.commenter_name,
                    "created_at": comment.created_at.isoformat()
                }

            except SQLAlchemyError as e:
                await db.rollback()
                logger.error(f"DB error adding comment to folder {folder_id}: {e}")
                return None
            except Exception as e:
                await db.rollback()
                logger.error(
                    f"Unexpected error adding comment to folder {folder_id}: {e}",
                    exc_info=True
                )
                return None

        return None
# Create a global instance
db_service = DBService() 