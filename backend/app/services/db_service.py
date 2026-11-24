import logging
import uuid
from typing import List, Optional, Union, Tuple
from sqlalchemy.future import select
from sqlalchemy import func, text, update, delete, insert, and_, or_, tuple_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timezone
from sqlalchemy import distinct
from sqlalchemy import Date, func




from app.models.paper import Paper
from app.models.db_models import DBPaper, DBAuthor, DBCategory, DBUser, DBSession, DBMessage, paper_authors,DBUserFile, DBEmailList, DBUserTopic,DBFolder,paper_categories,paper_authors,DBSharedFolder
from app.models.db_models import DBComment,shared_folder_comments
from app.db.database import get_async_db

from app.services.llm_service import llm_service 
from app.services.extract_info import paper_info_extractor

from fastapi import HTTPException, status
import re
import sqlalchemy as sa
logger = logging.getLogger(__name__)

FTS_CONFIG = "simple"

class DBService:
    """
    PostgreSQL database service to interact with database
    """
    
    def __init__(self):
        pass
    
    async def get_user_email(self, user_id) -> Optional[str]:
        """Return the stored email for a user id (uuid), or None."""
        try:
            uid = user_id if isinstance(user_id, uuid.UUID) else uuid.UUID(str(user_id))
        except (ValueError, TypeError):
            return None
        async for db in get_async_db():
            try:
                res = await db.execute(select(DBUser.email).where(DBUser.id == uid))
                return res.scalar_one_or_none()
            except SQLAlchemyError as e:
                logger.error(f"DB error getting user email: {e}")
                return None

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

    # ========== Search History Methods ==========
    
    async def add_search_history(
        self,
        session_id: str,
        user_id: str,
        query: str,
        timestamp: datetime
    ) -> bool:
        """
        Add search history record
        """
        try:
            async for db in get_async_db():
                # 这里可以创建一个搜索历史表，或者暂时记录到日志
                logger.info(f"Search history: user={user_id}, session={session_id}, query='{query}', time={timestamp}")
                return True
        except Exception as e:
            logger.error(f"Error adding search history: {e}")
            return False
    
    async def get_user_search_history(self, user_id: str) -> List[dict]:
        """
        Get user's search history
        """
        try:
            # 这里可以从数据库获取搜索历史，暂时返回空列表
            # 后续可以创建专门的搜索历史表
            logger.info(f"Getting search history for user: {user_id}")
            return []
        except Exception as e:
            logger.error(f"Error getting search history: {e}")
            return []
    
    async def save_search_context(
        self,
        context_data: dict
    ) -> bool:
        """
        Save search context for future reference
        """
        try:
            # 这里可以保存到数据库或缓存
            logger.info(f"Saving search context: {context_data}")
            return True
        except Exception as e:
            logger.error(f"Error saving search context: {e}")
            return False
    
    
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
    
    async def add_papers(self, papers: List[Paper], platform: str = None) -> List[str]:
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
                    select(DBPaper.paper_id)
                    .where(
                        and_(
                            DBPaper.paper_id.in_(incoming_ids),
                            DBPaper.platform == (platform or "pubmed")
                        )
                    )
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
                    # 如果没有指定平台，则使用Paper对象自己的platform，或者使用extract_platform来推断
                    paper_platform = platform or p.platform or paper_info_extractor.extract_platform(p.paper_id)
                    
                    # 检查论文是否已存在，考虑 paper_id 和 platform
                    check_result = await db.execute(
                        select(DBPaper.paper_id)
                        .where(
                            and_(
                                DBPaper.paper_id == p.paper_id,
                                DBPaper.platform == paper_platform
                            )
                        )
                    )
                    if check_result.scalar_one_or_none():
                        logger.info(f"Paper {p.paper_id} with platform {paper_platform} already exists, skipping")
                        continue
                    
                    db_p = DBPaper(
                        paper_id      = p.paper_id,
                        title         = p.title,
                        abstract      = p.abstract,
                        pdf_url       = p.pdf_url.replace("http://", "https://"),
                        published_date= p.published_date,
                        updated_date  = p.updated_date,
                        click_count   = 0,
                        embedding     = emb,   # ← 直接存 embedding 列
                        platform      = paper_platform  # 使用确定的平台
                    )
                    # 4.1 关联 categories
                    for cat in p.categories:
                        db_p.categories.append(existing_cats[cat])

                    db.add(db_p)
                    await db.flush()  # 以便有 paper_id

                    # 4.2 关联 authors（保留顺序）
                    for order, name in enumerate(p.authors):
                        try:
                            # 先检查是否已存在该作者记录
                            check_result = await db.execute(
                                text("""
                                SELECT 1 FROM paper_authors 
                                WHERE paper_id = :pid AND author = :auth 
                                LIMIT 1
                                """),
                                {"pid": p.paper_id, "auth": name}
                            )
                            exists = check_result.scalar() is not None
                            
                            if not exists:
                                await db.execute(
                                    text("""
                                    INSERT INTO paper_authors (paper_id, author, author_order, platform)
                                    VALUES (:pid, :auth, :ord, :platform)
                                    """),
                                    {"pid": p.paper_id, "auth": name, "ord": order, "platform": paper_platform}
                                )
                        except Exception as e:
                            logger.warning(f"Error inserting author {name} for paper {p.paper_id}: {e}")
                    
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
                ).where(DBPaper.platform == "arxiv")  # 默认只取 arxiv 平台的论文
                # no limit or offset → fetch all
            )
            db_papers = result.scalars().all()
            for db_paper in db_papers:
                if db_paper.platform == "upload":
                    logger.info(f"Paper {db_paper.paper_id} is uploaded, skipping")
                    continue
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
        
    async def get_paper_by_id(self, paper_id: str, platform: str = None) -> Optional[Paper]:
        """
        get paper Object by paper_id
        """
        logger.info(f"Looking up paper in database with ID: {paper_id}, platform: {platform}")

        if not paper_id:
            logger.warning("Attempted to get paper with empty ID")
            return None
            
        try:
            async for db in get_async_db():
                # 直接join一次性查到所有需要的字段
                stmt = (
                    select(
                        DBPaper,
                        func.array_agg(distinct(DBAuthor.name)).label("authors"),
                        func.array_agg(distinct(DBCategory.name)).label("categories")
                    )
                    .outerjoin(paper_authors, and_(
                        paper_authors.c.paper_id == DBPaper.paper_id,
                        paper_authors.c.platform == DBPaper.platform
                    ))
                    .outerjoin(DBAuthor, paper_authors.c.author == DBAuthor.name)
                    .outerjoin(paper_categories, and_(
                        paper_categories.c.paper_id == DBPaper.paper_id,
                        paper_categories.c.platform == DBPaper.platform
                    ))
                    .outerjoin(DBCategory, paper_categories.c.category == DBCategory.name)
                    .where(and_(DBPaper.paper_id == paper_id, DBPaper.platform == platform))
                    .group_by(DBPaper)
                )
                
                result = await db.execute(stmt)
                record = result.first()
                
                if not record:
                    logger.info(f"Paper with ID {paper_id} and platform {platform} not found in database")
                    return None
                    
                db_paper = record[0]
                authors = record[1] if record[1] and record[1][0] is not None else []
                categories = record[2] if record[2] and record[2][0] is not None else []
                
                paper = Paper(
                    paper_id=db_paper.paper_id,
                    title=db_paper.title,
                    authors=authors,
                    abstract=db_paper.abstract,
                    categories=categories,
                    pdf_url=db_paper.pdf_url,
                    published_date=db_paper.published_date,
                    updated_date=db_paper.updated_date,
                    platform=db_paper.platform
                )
                
                logger.info(f"success get paper: {paper.title} (ID: {paper.paper_id}, platform: {paper.platform})")
                return paper
        except SQLAlchemyError as e:
            logger.error(f"Database error when getting paper by ID {paper_id} and platform {platform}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error when getting paper by ID {paper_id} and platform {platform}: {str(e)}", exc_info=True)
            return None
        
        logger.warning(f"Paper lookup completed with no result for ID: {paper_id}, platform: {platform}")
        return None

    async def get_papers_by_ids(self, paper_ids_data: List[Union[str, Tuple[str, str]]]) -> List[Paper]:
        """
        Get paper Objects by a list of paper_ids or tuples of (paper_id, platform)
        """
        if not paper_ids_data:
            return []
            
        logger.info(f"get_papers_by_ids received data: {paper_ids_data[:3]}...")  # 只显示前3个
        
        # 提取paper_id和platform
        paper_ids = []
        paper_platforms = {}
        for item in paper_ids_data:
            if isinstance(item, tuple) and len(item) == 2:
                paper_id, platform = item
                # 确保都是字符串
                paper_id = str(paper_id)
                platform = str(platform)
                paper_ids.append(paper_id)
                paper_platforms[paper_id] = platform
            else:
                paper_id = str(item)  # 确保是字符串
                paper_ids.append(paper_id)
                paper_platforms[paper_id] = "arxiv"  # 默认平台
        
        logger.info(f"Processed paper_ids: {paper_ids[:3]}...")
        logger.info(f"Processed platforms: {list(paper_platforms.values())[:3]}...")
        
        try:
            async for db in get_async_db():
                # 构建查询条件列表
                conditions = []
                for paper_id in paper_ids:
                    platform = paper_platforms.get(paper_id, "arxiv")
                    # 再次确保参数都是字符串类型
                    paper_id_str = str(paper_id)
                    platform_str = str(platform)
                    logger.debug(f"Adding condition: paper_id={paper_id_str} (type: {type(paper_id_str)}), platform={platform_str} (type: {type(platform_str)})")
                    conditions.append(
                        and_(
                            DBPaper.paper_id == paper_id_str,
                            DBPaper.platform == platform_str
                        )
                    )
                
                # 如果没有条件，直接返回空列表
                if not conditions:
                    return []
                
                # 使用复杂的查询一次性获取所有论文及其作者、分类
                stmt = (
                    select(
                        DBPaper.paper_id,
                        DBPaper.platform,
                        DBPaper.title,
                        DBPaper.abstract,
                        DBPaper.pdf_url,
                        DBPaper.published_date,
                        DBPaper.updated_date,
                        func.array_agg(distinct(DBAuthor.name)).label("authors"),
                        func.array_agg(distinct(DBCategory.name)).label("categories")
                    )
                    .outerjoin(paper_authors, and_(
                        paper_authors.c.paper_id == DBPaper.paper_id,
                        paper_authors.c.platform == DBPaper.platform
                    ))
                    .outerjoin(DBAuthor, paper_authors.c.author == DBAuthor.name)
                    .outerjoin(paper_categories, and_(
                        paper_categories.c.paper_id == DBPaper.paper_id,
                        paper_categories.c.platform == DBPaper.platform
                    ))
                    .outerjoin(DBCategory, paper_categories.c.category == DBCategory.name)
                    .where(or_(*conditions))
                    .group_by(
                        DBPaper.paper_id,
                        DBPaper.platform,
                        DBPaper.title,
                        DBPaper.abstract,
                        DBPaper.pdf_url,
                        DBPaper.published_date,
                        DBPaper.updated_date
                    )
                )
                
                result = await db.execute(stmt)
                records = result.all()
                
                # 将结果转换为Paper对象列表
                papers = []
                for record in records:
                    paper_id = record[0]
                    platform = record[1]
                    authors = record[7] if record[7] and record[7][0] is not None else []
                    categories = record[8] if record[8] and record[8][0] is not None else []
                    
                    paper = Paper(
                        paper_id=paper_id,
                        platform=platform,
                        title=record[2],
                        abstract=record[3],
                        pdf_url=record[4],
                        published_date=record[5],
                        updated_date=record[6],
                        authors=authors,
                        categories=categories
                    )
                    papers.append(paper)
                
                return papers
                
        except SQLAlchemyError as e:
            logger.error(f"Database error when getting papers by IDs: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error when getting papers by IDs: {str(e)}", exc_info=True)
            return []
        
        return []


    
    

    async def get_recent_papers(self, limit: int = 30, keyword: str = None, offset: int = 0) -> List[Paper]:
        async for db in get_async_db():
            # 第一步：纯轻量列（可 Index-Only Scan）
            cols = (
                DBPaper.paper_id, DBPaper.platform,
                DBPaper.title, DBPaper.pdf_url, DBPaper.published_date
            )
            conditions = [
                DBPaper.platform != "upload",
                DBPaper.published_date.isnot(None),
                DBPaper.published_date <= func.now(),
            ]
            if keyword:
                conditions.append(DBPaper.title.ilike(f"%{keyword}%"))

            base = (
                select(*cols)
                .where(*conditions)
                .order_by(DBPaper.published_date.desc(), DBPaper.paper_id.desc())
                .limit(limit).offset(offset)
            )
            rows = (await db.execute(base)).all()
            if not rows:
                return []

            keys = [(r.paper_id, r.platform) for r in rows]

            # 第二步：仅把这 batch 的对象连同作者/分类取回
            q2 = (
                select(DBPaper)
                .options(selectinload(DBPaper.authors), selectinload(DBPaper.categories))
                .where(tuple_(DBPaper.paper_id, DBPaper.platform).in_(keys))
            )
            objs = (await db.execute(q2)).scalars().all()
            mp = {(o.paper_id, o.platform): o for o in objs}

            # 按第一步顺序组装返回
            out: List[Paper] = []
            for r in rows:
                p = mp.get((r.paper_id, r.platform))
                if not p:
                    continue
                out.append(Paper(
                    paper_id=p.paper_id,
                    title=p.title,
                    authors=[a.name for a in p.authors],
                    abstract=p.abstract,
                    categories=[c.name for c in p.categories],
                    pdf_url=p.pdf_url.replace("http://", "https://"),
                    published_date=p.published_date,
                    updated_date=p.updated_date,
                    platform=p.platform,
                ))
            return out

    
    

    async def count_papers(self) -> int:
        async for db in get_async_db():
            v = (await db.execute(text(
                "SELECT total_count FROM public.paper_counters WHERE id=1"
            ))).scalar()
            if v is not None:
                return int(v)
            # 兜底：计数表丢了或未初始化时，紧急回退一次
            v = (await db.execute(text("SELECT COUNT(*) FROM public.papers"))).scalar()
            # 同步写回（防止并发冲突可忽略失败）
            await db.execute(text("""
                INSERT INTO public.paper_counters(id, total_count)
                VALUES (1, :v)
                ON CONFLICT (id) DO UPDATE SET total_count = EXCLUDED.total_count
            """), {"v": int(v)})
            await db.commit()
            return int(v)
    
    async def click_paper(self, paper_id: str, platform: str = "arxiv") -> bool:
        """
        Record a click on a paper
        """
        if not paper_id:
            return False
            
        try:
            async for db in get_async_db():
                # First, check if paper exists
                stmt = select(DBPaper).where(and_(
                    DBPaper.paper_id == paper_id,
                    DBPaper.platform == platform
                ))
                result = await db.execute(stmt)
                paper = result.scalar_one_or_none()
                
                if not paper:
                    logger.warning(f"Paper {paper_id} with platform {platform} not found for click recording")
                    return False
                    
                # Update click count
                paper.click_count += 1
                await db.commit()
                
                logger.info(f"Successfully recorded click for paper ID: {paper_id}, platform: {platform}")
                return True
                
        except SQLAlchemyError as e:
            logger.error(f"Database error when recording click for paper ID {paper_id}, platform {platform}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error when recording click for paper ID {paper_id}, platform {platform}: {str(e)}", exc_info=True)
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
            
    async def add_file_to_user(self, user_id: int, paper_id: str, platform: str = "arxiv") -> bool:
        """
        把 paper 放进用户的"默认文件夹"：
        1. 找到 user→folders.name=='default'；若不存在就创建
        2. 在该 folder 内插入 (folder_id, paper_id, platform)
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
                    select(DBPaper).where(and_(
                        DBPaper.paper_id == paper_id,
                        DBPaper.platform == platform
                    )))
                ).scalars().first()
                if not paper:
                    logger.info(f"paper {paper_id} (platform: {platform}) not found")
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

                # -------- 3) 插入 (folder_id, paper_id, platform) --------
                entry = DBUserFile(folder_id=folder.id, paper_id=paper_id, platform=platform)
                db.add(entry)
                await db.commit()
                return True

            except IntegrityError:
                # 同一 folder 已有这篇 paper，无需重复
                await db.rollback()
                logger.info(
                    f"paper {paper_id} (platform: {platform}) already in user {user_id}'s default folder"
                )
                return True

            except SQLAlchemyError as e:
                await db.rollback()
                logger.error(f"DB error adding file to default folder: {e}")
                return False
    async def add_file_to_folder(self,folder_id: int, paper_id: str, platform: str = "arxiv") -> bool:
        # 检查 folder 属于 user
        async for db in get_async_db():
            folder = (await db.execute(
                select(DBFolder)
                  .where(DBFolder.id==folder_id)
            )).scalars().first()
            if not folder:
                return False
            entry = DBUserFile(folder_id=folder_id, paper_id=paper_id, platform=platform)
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

    async def remove_file_from_user(self, user_id: int, paper_id: str, platform: str = "arxiv") -> bool:
        """
        删除 (paper_id, platform) 在用户任意文件夹中的记录。
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
                    .where(and_(
                        DBUserFile.paper_id == paper_id,
                        DBUserFile.platform == platform
                    ))
                    .where(
                        DBUserFile.folder_id.in_(
                            select(DBFolder.id)
                            .where(DBFolder.user_id == user_id)
                            .scalar_subquery()
                        )
                    )
                )
                    
                result = await db.execute(stmt)
                await db.commit()
                    
                if result.rowcount > 0:
                    logger.info(
                        f"removed paper {paper_id} (platform: {platform}) ({result.rowcount} rows) "
                        f"from user {user_id}'s folders"
                    )
                    return True
                
                # ---------- 2. 只尝试 default 文件夹 ----------
                # 看来所有文件夹里都没有，再尝试只找默认文件夹
                default_id = (await db.execute(
                    select(DBFolder.id)
                    .where(DBFolder.user_id == user_id, DBFolder.name == "default")
                )).scalar()
                
                if not default_id:
                    logger.info(f"file {paper_id} (platform: {platform}) not found for user {user_id}")
                    return False
                    
                result = await db.execute(
                    delete(DBUserFile)
                    .where(and_(
                        DBUserFile.folder_id == default_id,
                        DBUserFile.paper_id == paper_id,
                        DBUserFile.platform == platform
                    ))
                )
                await db.commit()
                    
                if result.rowcount > 0:
                    logger.info(f"removed paper {paper_id} (platform: {platform}) from user {user_id}'s default folder")
                    return True
                else:
                    logger.info(f"file {paper_id} (platform: {platform}) not found for user {user_id}")
                    return False
                    
            except SQLAlchemyError as e:
                await db.rollback()
                logger.error(
                    f"DB error deleting paper {paper_id} (platform: {platform}) for user {user_id}: {e}"
                )
                return False
        
        return False

    async def remove_file_from_folder(
        self,
        user_id: int,
        folder_id: int,
        paper_id: str,
        platform: str = "arxiv"
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
                        DBUserFile.paper_id  == paper_id,
                        DBUserFile.platform == platform
                    )
                )
                result = await db.execute(stmt)
                await db.commit()

                if result.rowcount and result.rowcount > 0:
                    logger.info(f"removed paper {paper_id} (platform: {platform}) from folder {folder_id}")
                    return True
                else:
                    logger.info(f"paper {paper_id} (platform: {platform}) not in folder {folder_id}")
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
    
    async def get_folders_with_files(self, user_id: uuid.UUID) -> List[dict]:
        async for db in get_async_db():
            # 1. 查出用户 own 的 folders
            stmt_own = (
                select(DBFolder)
                .options(
                    selectinload(DBFolder.files)
                    .selectinload(DBUserFile.paper)
                )
                .where(DBFolder.user_id == user_id)
                .order_by(DBFolder.created_at)
            )
            own_res = await db.execute(stmt_own)
            own_folders: List[DBFolder] = own_res.scalars().all()

            # 2. 查出用户作为 editor 的 shared folders
            stmt_shared = (
                select(DBSharedFolder.folder_id)
                .where(DBSharedFolder.allowed_editor_ids.any(user_id))
            )
            shared_res = await db.execute(stmt_shared)
            shared_folder_ids = {fid for (fid,) in shared_res.all()}

            # 3. 将 own_folders 和 shared_folders 合并，去重
            #    并为 shared folders 预加载 files
            all_folder_ids = {fld.id for fld in own_folders} | shared_folder_ids

            stmt_all = (
                select(DBFolder)
                .options(
                    selectinload(DBFolder.files)
                    .selectinload(DBUserFile.paper)
                )
                .where(DBFolder.id.in_(all_folder_ids))
                .order_by(DBFolder.created_at)
            )
            all_res = await db.execute(stmt_all)
            folders: List[DBFolder] = all_res.scalars().all()

            # 4. 组装输出
            out = []
            for fld in folders:
                is_own = (str(fld.user_id) == str(user_id))
                #print(fld.id, fld.name, fld.user_id, user_id, is_own)
                out.append({
                    "id":        fld.id,
                    "name":      fld.name,
                    "type":      "own" if is_own else "shared",
                    "files": [
                        {
                            "paper_id":  uf.paper_id,
                            "platform":  uf.platform,
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

        # 理论不会走到这里
        return []



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
    async def get_folder_role(self, folder_id: int, user_id) -> Optional[str]:
        """
        Resolve a user's role on a folder: 'owner' | 'editor' | 'viewer' | None (no access).
        owner  = folders.user_id; editor/viewer = listed in the folder's shared_folders row;
        any signed-in user is a viewer if the shared folder is public.
        """
        try:
            uid = user_id if isinstance(user_id, uuid.UUID) else uuid.UUID(str(user_id))
        except (ValueError, TypeError, AttributeError):
            return None
        async for db in get_async_db():
            try:
                folder = await db.get(DBFolder, folder_id)
                if folder is None:
                    return None
                if folder.user_id == uid:
                    return "owner"
                res = await db.execute(select(DBSharedFolder).where(DBSharedFolder.folder_id == folder_id))
                shared = res.scalar_one_or_none()
                if shared is None:
                    return None
                if shared.owner_id == uid:
                    return "owner"
                if uid in (shared.allowed_editor_ids or []):
                    return "editor"
                if shared.is_public or uid in (shared.allowed_user_ids or []):
                    return "viewer"
                return None
            except SQLAlchemyError as e:
                logger.error(f"DB error resolving folder role: {e}")
                return None

    async def get_folder(self, folder_id: int) -> DBFolder | None:
        async for db in get_async_db():
            return await db.get(DBFolder, folder_id)

    async def get_files_by_folder_id(self, folder_id: int) -> list[dict]:
        """
        根据 folder_id 返回该文件夹下所有文件的扁平列表，附带 embedding。
        """
        async for db in get_async_db():
            try:
                # ① 预加载 paper 及其 authors，避免 N+1
                stmt = (
                    select(DBUserFile)
                    .options(
                        selectinload(DBUserFile.paper)
                            .selectinload(DBPaper.authors)
                    )
                    .where(DBUserFile.folder_id == folder_id)
                    .order_by(DBUserFile.added_at)
                )
                result = await db.execute(stmt)
                user_files: list[DBUserFile] = result.scalars().all()

                # ② 拼装返回结构（新增 embedding）
                return [
                    {
                        # —— 来自 user_files 表 —— #
                        "paper_id":       uf.paper_id,
                        "platform":       uf.platform,
                        "added_at":       uf.added_at.isoformat(),
                        "folder_id":      uf.folder_id,
                        "selected":       bool(uf.selected),

                        # —— 来自 papers 表 —— #
                        "title":          uf.paper.title,
                        "abstract":       uf.paper.abstract,
                        "pdf_url":        uf.paper.pdf_url,
                        "published_date": uf.paper.published_date.isoformat(),
                        "updated_date":   (
                            uf.paper.updated_date.isoformat()
                            if uf.paper.updated_date else None
                        ),
                        "click_count":    uf.paper.click_count,

                        # —— 新增字段 —— #
                        "authors":        [a.name for a in uf.paper.authors],
                        "embedding": (
                            [float(x) for x in uf.paper.embedding]
                            if uf.paper.embedding is not None else None
                        ),
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

    async def get_shared_folders(self, user_id: uuid.UUID) -> list[dict]:
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
                tmp=[]
                for sf in shared:
                    print(sf.is_public, user_id, sf.owner_id, sf.allowed_user_ids)
                    if sf.is_public:  # 只返回公开的共享文件夹
                        tmp.append(sf)
                    elif str(user_id) == str(sf.owner_id):  # 只返回用户自己的共享文件夹
                        tmp.append(sf)
                    elif str(user_id) in str(sf.allowed_user_ids):  # 只返回用户有权限的共享文件夹
                        tmp.append(sf)
                    elif str(user_id) in str(sf.allowed_editor_ids):  # 只返回用户有编辑权限的共享文件夹
                        tmp.append(sf)

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
                    for sf in tmp
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
        paper_id: str,
        selected: bool,
        platform: str = "arxiv"
    ) -> bool:
        """
        Update the selected flag for a paper file
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
                logger.info(f"Updated selection for paper {paper_id} (platform: {platform}) to {selected} for user {user_id}")
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
    
    async def get_comments_by_folder_id(self, folder_id: int) -> list[dict]:
        async for db in get_async_db():
            # ① 找到真正的 shared_folder.id
            result = await db.execute(
                select(DBSharedFolder.id)
                .where(DBSharedFolder.folder_id == folder_id)
            )
            shared_row = result.first()
            if not shared_row:
                return []          # 说明这个文件夹没被分享

            shared_id = shared_row.id

            # ② 再去 pivot + comments 表查
            result = await db.execute(
                select(
                    DBComment.id,
                    DBComment.content,
                    DBComment.commenter_name,
                    DBComment.created_at,
                    DBComment.commenter_id,
                )
                .join(
                    shared_folder_comments,
                    DBComment.id == shared_folder_comments.c.comment_id,
                )
                .where(shared_folder_comments.c.shared_folder_id == shared_id)
                .order_by(DBComment.created_at)
            )
            rows = result.all()

            return [
                {
                    "id": r.id,
                    "content": r.content,
                    "commenter_name": r.commenter_name,
                    "commenter_id": r.commenter_id,
                    "created_at": r.created_at.isoformat(),
                }
                for r in rows
            ]
        return []

        
    async def add_comment_by_folder_id(self, user_id, folder_id, content):
        content = content.strip()
        if not content:
            return None

        async for db in get_async_db():
            try:
                # 1) 查 SharedFolder（注意这里是 shared_folders.id <- folders.id）
                result = await db.execute(
                    select(DBSharedFolder)
                    .where(DBSharedFolder.folder_id == folder_id)
                )
                shared = result.scalars().first()
                if not shared:
                    return None

                # 2) 查 user 名称
                user = await db.get(DBUser, user_id)
                commenter_name = user.name if user else ""

                # 3) 创建评论实体
                comment = DBComment(
                    content=content,
                    commenter_id=user_id,
                    commenter_name=commenter_name,
                    created_at=datetime.utcnow()
                )
                db.add(comment)
                # 拿到 comment.id
                await db.flush()

                # 4) 手动插入关系表
                await db.execute(
                    insert(shared_folder_comments).values(
                        shared_folder_id=shared.id,
                        comment_id=comment.id
                    )
                )

                # 5) 提交并刷新
                await db.commit()
                await db.refresh(comment)

                return {
                    "id": comment.id,
                    "content": comment.content,
                    "commenter_name": comment.commenter_name,
                    "commenter_id": comment.commenter_id,
                    "created_at": comment.created_at.isoformat()
                }

            except SQLAlchemyError:
                await db.rollback()
                return None

        return None
    
    async def delete_comment(
        self,
        cid: int,
        user_id: Optional[uuid.UUID] = None, 
    ) -> bool:
        """
        删除一条评论及其在 pivot 表中的关联行。  
        - 若指定 `user_id`，则只有该用户本人才能删除；否则返回 False。  
        - 成功返回 True；评论不存在或无权限返回 False。

        Args:
            cid (int): comments.id
            user_id (UUID|None): 当前登录用户 ID（可选）

        Returns:
            bool: 删除成功 ➜ True；失败/无权限 ➜ False
        """
        async for db in get_async_db():        # type: AsyncSession
            try:
                # ① 先取评论
                comment: DBComment | None = await db.get(DBComment, cid)
                if comment is None:
                    logger.warning(f"Comment {cid} not found")
                    return False

                # ② 权限校验（可选）
                if user_id is not None and comment.commenter_id != user_id:
                    logger.warning(
                        f"User {user_id} tried to delete others' comment {cid}"
                    )
                    return False

                # ③ 删 pivot 表行（若未设置 CASCADE）
                await db.execute(
                    delete(shared_folder_comments).where(
                        shared_folder_comments.c.comment_id == cid
                    )
                )

                # ④ 删评论本身
                await db.delete(comment)
                await db.commit()
                logger.info(f"Deleted comment {cid} by user {user_id}")
                return True

            except SQLAlchemyError as e:
                await db.rollback()
                logger.error(f"DB error deleting comment {cid}: {e}")
                return False

        # 理论到不了这里（除非 get_async_db() 无 db）
        return False

    async def get_folder_summary(
        self,
        folder_id: int,
    ) -> Optional[str]:
        """
        根据 folder_id 取 shared_folders.summary。

        - 若传入 user_id，则只返回该用户本人拥有的或公开分享的概要。
        - 找不到记录返回 None（可区分"无记录" vs. "summary 为空字符串"）。
        """
        async for db in get_async_db():                 # type: AsyncSession
            try:
                stmt = select(DBSharedFolder.summary).where(
                    DBSharedFolder.folder_id == folder_id
                )

                result = await db.execute(stmt)
                summary = result.scalar_one_or_none()   # None 或 str

                return summary

            except SQLAlchemyError as e:
                await db.rollback()
                logger.error(f"DB error in get_folder_summary: {e}")
                return None

        # 理论上不会到这一步
        return None
    async def add_folder_summary(self,folder_id, summary):
        """
        添加或更新文件夹的概要信息。
        如果已存在，则更新；否则插入新记录。
        """
        async for db in get_async_db():
            try:
                # 1) 检查是否已存在该 folder_id 的记录
                existing = await db.execute(
                    select(DBSharedFolder).where(DBSharedFolder.folder_id == folder_id)
                )
                shared_folder = existing.scalars().first()

                if shared_folder:
                    # 更新现有记录
                    shared_folder.summary = summary
                else:
                    # 创建新记录
                    shared_folder = DBSharedFolder(
                        folder_id=folder_id,
                        summary=summary,
                        created_at=datetime.utcnow()
                    )
                    db.add(shared_folder)

                await db.commit()
                return True

            except SQLAlchemyError as e:
                await db.rollback()
                logger.error(f"DB error in add_folder_summary: {e}")
                return False

        return False

    async def get_share_permission(
        self, folder_id: int
    ) -> List[dict[str, str]]:
        """
        返回指定 shared folder 的访问权限列表：
        - 文件夹不存在 → 404
        - is_public=True 或 两个名单都为空 → 返回 []
        - 否则返回 [{email, role}, ...]，role ∈ {'viewer','editor'}
        """
        async for db in get_async_db():  # type: AsyncSession
            try:
                # ① 读 public 标志，以及 viewer/editor 两个数组
                stmt = select(
                    DBSharedFolder.is_public,
                    DBSharedFolder.allowed_user_ids,
                    DBSharedFolder.allowed_editor_ids,
                ).where(DBSharedFolder.folder_id == folder_id)
                res = await db.execute(stmt)
                row = res.one_or_none()
                if row is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Shared folder #{folder_id} not found",
                    )

                is_public, viewers, editors = row
                viewers = viewers or []
                editors = editors or []

                # 如果公开或都没指定，直接返回空
                if is_public or (not viewers and not editors):
                    return []

                # ② 整合所有要 lookup 的用户 ID
                viewer_ids = set(viewers)
                editor_ids = set(editors)
                all_ids = list(viewer_ids | editor_ids)

                # ③ 批量查询 email
                email_res = await db.execute(
                    select(DBUser.id, DBUser.email).where(DBUser.id.in_(all_ids))
                )
                rows = email_res.all()  # List of (UUID, str)

                # ④ 构造 id -> email 映射
                id2email = {uid: email for uid, email in rows}

                # ⑤ 按原顺序组装结果，editor 覆盖 viewer
                result: List[Dict[str, str]] = []
                for uid in all_ids:
                    email = id2email.get(uid)
                    if not email:
                        # 数据库中找不到此用户，跳过
                        continue
                    role = 'editor' if uid in editor_ids else 'viewer'
                    result.append({"email": email, "role": role})

                return result

            except SQLAlchemyError as e:
                logger.error(f"DB error in get_share_permission: {e}")
                return []

        # 理论上走不到这里
        return []

    async def update_share_mode(
        self,
        folder_id: int,        # ← 原始 folder_id，而非 shared_folders.id
        is_public: bool
    ) -> bool:
        """
        更新共享文件夹的公开状态（is_public）。
        返回 True 表示更新成功；False 表示未找到或出错。
        """
        async for db in get_async_db():
            try:
                # ① 用 folder_id 字段查询（假设唯一）
                stmt = select(DBSharedFolder).where(DBSharedFolder.folder_id == folder_id)
                res = await db.execute(stmt)
                shared_folder: DBSharedFolder | None = res.scalar_one_or_none()

                if not shared_folder:
                    logger.info(f"Shared folder with folder_id={folder_id} not found")
                    return False

                # ② 更新 is_public
                shared_folder.is_public = is_public
                await db.commit()

                logger.info(
                    f"Updated share mode for folder_id={folder_id} → is_public={is_public}"
                )
                return True

            except SQLAlchemyError as e:
                await db.rollback()
                logger.error(
                    f"DB error updating share mode for folder_id={folder_id}: {e}"
                )
                return False

            except Exception as e:
                await db.rollback()
                logger.error(
                    f"Unexpected error updating share mode for folder_id={folder_id}: {e}",
                    exc_info=True,
                )
                return False

        return False   # 理论上不会走到这里

    async def get_share_mode(self, folder_id: int) -> bool:
        """
        获取共享文件夹的公开状态（is_public）。
        返回 True 表示公开；False 表示私有。
        """
        async for db in get_async_db():
            try:
                stmt = select(DBSharedFolder.is_public).where(DBSharedFolder.folder_id == folder_id)
                res = await db.execute(stmt)
                is_public = res.scalar_one_or_none()
                return is_public

            except SQLAlchemyError as e:
                logger.error(f"DB error getting share mode for folder_id={folder_id}: {e}")
                return False

            except Exception as e:
                logger.error(f"Unexpected error getting share mode for folder_id={folder_id}: {e}", exc_info=True)
                return False


    async def add_share_user(self, folder_id: int, user_id: uuid.UUID, role: str) -> bool:
        """
        向共享文件夹的 `allowed_user_ids` 中追加一个用户。
        - 找不到 folder_id      → False
        - 用户已在名单内        → False
        - 其它异常 / 回滚失败    → False
        - 成功写入并 commit     → True
        """
        async for db in get_async_db():                 # type: AsyncSession
            try:
                # ① 仍然按 folder_id 字段查询，而非主键
                stmt = select(DBSharedFolder).where(DBSharedFolder.folder_id == folder_id)
                res = await db.execute(stmt)
                shared: DBSharedFolder | None = res.scalar_one_or_none()

                if shared is None:
                    logger.info(f"Shared folder with folder_id={folder_id} not found")
                    return False

                # ② 若列为 NULL，先初始化
                if role=="editor":
                    if shared.allowed_editor_ids is None:
                        shared.allowed_editor_ids = []
                    if user_id in shared.allowed_editor_ids:
                        logger.info(f"User {user_id} already exists in folder {folder_id}")
                        return False
                    new_ids = (shared.allowed_editor_ids or []) + [user_id]
                    shared.allowed_editor_ids = new_ids          # ★ 重新赋值，ORM 能检测到
                elif role=="viewer":
                    if shared.allowed_user_ids is None:
                        shared.allowed_user_ids = []

                    # ③ 幂等性检查
                    if user_id in shared.allowed_user_ids:
                        logger.info(f"User {user_id} already exists in folder {folder_id}")
                        return False
            
                    new_ids = (shared.allowed_user_ids or []) + [user_id]
                    shared.allowed_user_ids = new_ids          # ★ 重新赋值，ORM 能检测到
                await db.commit()
                logger.info(f"Added user {user_id} to shared folder {folder_id}")
                return True

            except SQLAlchemyError as e:
                await db.rollback()
                logger.error(f"DB error adding user {user_id} to folder {folder_id}: {e}")
                return False

            except Exception as e:
                await db.rollback()
                logger.error(
                    f"Unexpected error adding user {user_id} to folder {folder_id}: {e}",
                    exc_info=True,
                )
                return False

        return False    # 理论上不会走到这里

    async def update_share_user_role(
        self, folder_id: int, user_id: uuid.UUID, new_role: str
    ) -> bool:
        """
        """
        if new_role not in ("viewer", "editor"):
            logger.info(f"Invalid role '{new_role}' for folder {folder_id}")
            return False

        async for db in get_async_db():  # type: AsyncSession
            try:
                # ① 查 shared_folder 行（按 folder_id 字段）
                stmt = select(DBSharedFolder).where(DBSharedFolder.folder_id == folder_id)
                res = await db.execute(stmt)
                shared: Optional[DBSharedFolder] = res.scalar_one_or_none()

                if shared is None:
                    logger.info(f"Shared folder with folder_id={folder_id} not found")
                    return False

                # 初始化两个字段为空列表，以便后面操作
                viewers = shared.allowed_user_ids or []
                editors = shared.allowed_editor_ids or []

                # ② 根据 new_role 做移动
                if new_role == "viewer":
                    # 从 editors 中移除
                    if user_id in editors:
                        editors = [uid for uid in editors if uid != user_id]
                    # 添加到 viewers（幂等）
                    if user_id not in viewers:
                        viewers = viewers + [user_id]

                else:  # new_role == "editor"
                    # 从 viewers 中移除
                    if user_id in viewers:
                        viewers = [uid for uid in viewers if uid != user_id]
                    # 添加到 editors（幂等）
                    if user_id not in editors:
                        editors = editors + [user_id]

                # ③ 赋值并 commit
                shared.allowed_user_ids = viewers
                shared.allowed_editor_ids = editors
                await db.commit()

                logger.info(
                    f"Updated role for user {user_id} in folder {folder_id} to '{new_role}'"
                )
                return True

            except SQLAlchemyError as e:
                await db.rollback()
                logger.error(f"DB error updating role for user {user_id} in folder {folder_id}: {e}")
                return False

            except Exception as e:
                await db.rollback()
                logger.error(
                    f"Unexpected error updating role for user {user_id} in folder {folder_id}: {e}",
                    exc_info=True,
                )
                return False

        return False  # 理论上不会走到这里

    async def remove_share_user(self, folder_id: int, user_id: uuid.UUID) -> bool:
        """
        从共享文件夹的 `allowed_user_ids` 中移除一个用户（无需 MutableList）。
        - 找不到 folder_id          → False
        - 用户本就不在名单内        → False
        - 其它异常 / 回滚失败        → False
        - 成功写入并 commit         → True
        """
        async for db in get_async_db():                 # type: AsyncSession
            try:
                # ① 用 folder_id 字段查询
                stmt = select(DBSharedFolder).where(DBSharedFolder.folder_id == folder_id)
                res = await db.execute(stmt)
                shared: DBSharedFolder | None = res.scalar_one_or_none()

                if shared is None:
                    logger.info(f"Shared folder with folder_id={folder_id} not found")
                    return False

                curr_ids = shared.allowed_user_ids or []

                if user_id not in curr_ids:
                    logger.info(f"User {user_id} not in folder {folder_id}")
                    return False

                # ② 重新构造新列表并赋值（ORM 能检测到变化）
                shared.allowed_user_ids = [uid for uid in curr_ids if uid != user_id]

                # ③ 提交
                await db.commit()
                logger.info(f"Removed user {user_id} from shared folder {folder_id}")
                return True

            except SQLAlchemyError as e:
                await db.rollback()
                logger.error(f"DB error removing user {user_id} from folder {folder_id}: {e}")
                return False

            except Exception as e:
                await db.rollback()
                logger.error(
                    f"Unexpected error removing user {user_id} from folder {folder_id}: {e}",
                    exc_info=True,
                )
                return False

        return False    # 理论上不会走到这里
    


    
   # async def keyword_search(
    #    self,
   #     query: str,
    #    limit: int = 50,
    #) -> List[Tuple[str, str]]:
     #   """
      #  关键词检索（基于 GIN(tsv)）
   #     - 拆空白并用 AND 连接：'a b' -> 'a & b'
    #    - 主路径：to_tsquery(:cfg, unaccent(:q))
     #   - 兜底：websearch_to_tsquery(:cfg, unaccent(:q))
      #  """
       # if not query or not query.strip():
        #    return []

        # AND 形式（to_tsquery 语法）
#        terms = re.split(r"\s+", query.strip())
 #       processed_query = " & ".join(t for t in terms if t)
  #      limit = max(1, min(int(limit), 1000))
 #       print(f"keyword_search: query='{query}', processed='{processed_query}', limit={limit}")

  #      async for db in get_async_db():  # type: AsyncSession
   #         try:
                # 主路径：配置使用 simple，并与 tsv 一样走 unaccent
    #            sql_to = sa.text("""
     #               SELECT paper_id, platform
      #              FROM papers
       #             WHERE tsv @@ to_tsquery(:cfg, unaccent(:q))
        #            ORDER BY ts_rank_cd(tsv, to_tsquery(:cfg, unaccent(:q))) DESC
         #           LIMIT :lim
    #            """)
     #           res = await db.execute(sql_to, {"cfg": FTS_CONFIG, "q": processed_query, "lim": limit})
      #          rows = res.fetchall()
       #         return [(row[0], row[1]) for row in rows]

  #          except SQLAlchemyError as e:
   #             logger.warning(f"to_tsquery failed, fallback to websearch_to_tsquery: {e}")
    #            try:
 #                   sql_web = sa.text("""
  #                      SELECT paper_id, platform
   #                     FROM papers
    #                    WHERE tsv @@ websearch_to_tsquery(:cfg, unaccent(:q))
     #                   ORDER BY ts_rank_cd(tsv, websearch_to_tsquery(:cfg, unaccent(:q))) DESC
      #                  LIMIT :lim
       #             """)
#                    res = await db.execute(sql_web, {"cfg": FTS_CONFIG, "q": query, "lim": limit})
 #                   rows = res.fetchall()
  #                  return [(row[0], row[1]) for row in rows]
   #             except SQLAlchemyError as e2:
    #                logger.error(f"DB error in keyword_search (fallback failed): {e2}")
     #               return []
      #      except Exception as e:
       #         logger.error("Unexpected error in keyword_search", exc_info=True)
        #        return []

    #    return []



    # 假设你原来有这个
    # from .db import get_async_db, AsyncSession
    # from .config import FTS_CONFIG   # 现在不需要 FTS_CONFIG 了

    #async def keyword_search(
      #  self,
     #   query: str,
    #    limit: int = 50,
   # ) -> List[Tuple[str, str]]:
      #  """
      #  关键词检索（基于 pg_trgm / search_text）
     #   - 使用 trigram 相似度，支持简单 typo（如 'randan walk' ≈ 'random walk'）
    #    - 依赖：
          #  - papers.search_text 列
        #    - GIN(search_text gin_trgm_ops) 索引
         #   - CREATE EXTENSION pg_trgm
       # """
        #if not query or not query.strip():
         #   return []

        #q = query.strip()
        #limit = max(1, min(int(limit), 1000))
        #print(f"keyword_search(trgm): query='{q}', limit={limit}")

       # async for db in get_async_db():  # type: AsyncSession
      #      try:
                # 可选：设置相似度阈值（决定 `%` 操作符的匹配标准）
           #     await db.execute(sa.text("SET pg_trgm.similarity_threshold = 0.3"))

          #      sql = sa.text("""
               #     SELECT paper_id, platform
              #      FROM papers
             #       WHERE search_text % :q
            #        ORDER BY similarity(search_text, :q) DESC
           #         LIMIT :lim
          #      """)
         #       res = await db.execute(sql, {"q": q, "lim": limit})
              #  rows = res.fetchall()

                # 如果你想兜底（避免某些很奇怪的 query 完全空结果），可以加一个 fallback：
             #   if not rows:
                    # 再退一步，用 ILIKE 包含匹配
            #        sql_fallback = sa.text("""
           #             SELECT paper_id, platform
          #              FROM papers
         #               WHERE search_text ILIKE '%' || :q || '%'
        #                ORDER BY similarity(search_text, :q) DESC
       #                 LIMIT :lim
      #              """)
    #                res2 = await db.execute(sql_fallback, {"q": q, "lim": limit})
     #               rows = res2.fetchall()

   #             return [(row[0], row[1]) for row in rows]

  #          except SQLAlchemyError as e:
     #           logger.error(f"DB error in keyword_search(trgm): {e}", exc_info=True)
    #            return []
   #         except Exception as e:
  #              logger.error("Unexpected error in keyword_search(trgm)", exc_info=True)
 #               return []
#
    #    return []
    

    async def keyword_search(
        self,
        query: str,
        limit: int = 50,
    ) -> List[Tuple[str, str]]:
        """
        关键词检索（极简 + 宽泛短路）

        策略：
        1) 先判断是否“过于宽泛”的单词，是的话直接 return []，不查库。
        2) 否则：
        - 短 phrase（<=3 词，长度<=40）：title ILIKE '%phrase%'，按 published_date DESC 排。
        - 其它：title trigram 相似度查询（pg_trgm），按 similarity 排。
        不做任何 ILIKE 兜底。
        """
        if not query or not query.strip():
            return []

        q_raw = query.strip()
        q = " ".join(q_raw.split())  # 压缩多余空格
        limit = max(1, min(int(limit), 1000))
        print(f"keyword_search(mixed-fast-no-fallback+drop-broad): query='{q}', limit={limit}")

        terms = [t.lower() for t in q.split(" ") if t]
        n_terms = len(terms)

        # ====== 0. 过于宽泛的单词：直接丢弃 ======
        if n_terms == 1:
            t = terms[0]
            # 条件：太短（<=10）
            if len(t) <= 10:
                # 日志里标一下，方便以后调规则
                print(f"keyword_search: drop too-broad single-term '{t}', skip DB query")
                return []  # 直接返回空列表

        # ====== 1. 短 phrase：ILIKE 子串搜索 ======
        is_short_phrase = (n_terms <= 3 and len(q) <= 40)

        async for db in get_async_db():  # type: AsyncSession
            try:
                if is_short_phrase:
                    # 例：subgraph matching / random walk
                    pattern = f"%{q}%"
                    sql_phrase = sa.text("""
                        SELECT paper_id, platform
                        FROM papers
                        WHERE title ILIKE :pattern
                        ORDER BY published_date DESC, paper_id DESC
                        LIMIT :lim
                    """)
                    res = await db.execute(sql_phrase, {"pattern": pattern, "lim": limit})
                    rows = res.fetchall()
                    return [(row[0], row[1]) for row in rows]

                else:
                    # ====== 2. 更长 query：trigram 相似度 ======
                    await db.execute(sa.text("SET LOCAL pg_trgm.similarity_threshold = 0.48"))

                    sql_trgm = sa.text("""
                        SELECT paper_id, platform
                        FROM papers
                        WHERE title % :q
                        ORDER BY similarity(title, :q) DESC
                        LIMIT :lim
                    """)
                    res = await db.execute(sql_trgm, {"q": q, "lim": limit})
                    rows = res.fetchall()
                    return [(row[0], row[1]) for row in rows]

            except SQLAlchemyError as e:
                logger.error(
                    f"DB error in keyword_search(mixed-fast-no-fallback+drop-broad): {e}",
                    exc_info=True,
                )
                return []
            except Exception as e:
                logger.error(
                    "Unexpected error in keyword_search(mixed-fast-no-fallback+drop-broad)",
                    exc_info=True,
                )
                return []

        return []
# Create a global instance
db_service = DBService() 