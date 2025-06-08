import logging
from typing import List, Optional
from sqlalchemy.future import select
from sqlalchemy import func, text, update, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime

from app.models.paper import Paper
from app.models.db_models import DBPaper, DBAuthor, DBCategory, DBUser, DBSession, DBMessage, paper_authors
from app.db.database import get_async_db

logger = logging.getLogger(__name__)

class DBService:
    """
    PostgreSQL database service to interact with database
    """
    
    def __init__(self):
        pass
    
    async def add_user(self, name: str, email: str) -> bool:
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
                    name=name,
                    email=email
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
        Add papers list to the database
        """
        if not papers:
            return []
            
        added_ids = []
        async for db in get_async_db():
            try:
                # First, get all existing paper IDs to avoid unnecessary processing
                existing_paper_ids = set()
                paper_ids_to_check = [paper.paper_id for paper in papers]
                
                if paper_ids_to_check:
                    result = await db.execute(
                        select(DBPaper.paper_id).where(DBPaper.paper_id.in_(paper_ids_to_check))
                    )
                    existing_paper_ids = set(result.scalars().all())
                
                # Filter out papers that already exist
                papers_to_add = [
                    paper for paper in papers 
                    if paper.paper_id not in existing_paper_ids
                ]
                
                if not papers_to_add:
                    logger.info("All papers already exist in database, skipping")
                    return []
                
                logger.info(f"Processing {len(papers_to_add)} new papers (skipped {len(papers) - len(papers_to_add)} existing papers)")
                
                # Collect all author and category names
                all_author_names = set()
                all_category_names = set()
                
                for paper in papers_to_add:
                    all_author_names.update(paper.authors)
                    all_category_names.update(paper.categories)
                
                # Query existing authors and categories
                existing_authors = {}
                if all_author_names:
                    result = await db.execute(
                        select(DBAuthor).where(DBAuthor.name.in_(all_author_names))
                    )
                    for author in result.scalars().all():
                        existing_authors[author.name] = author
                
                existing_categories = {}
                if all_category_names:
                    result = await db.execute(
                        select(DBCategory).where(DBCategory.name.in_(all_category_names))
                    )
                    for category in result.scalars().all():
                        existing_categories[category.name] = category
                
                # Create non-existing authors and categories at once
                authors_to_create = all_author_names - existing_authors.keys()
                if authors_to_create:
                    # Use VALUES clause to insert multiple authors at once
                    author_objects = [DBAuthor(name=name) for name in authors_to_create]
                    db.add_all(author_objects)
                    # Immediately commit author data
                    await db.flush()
                    
                    # Query again to get all authors
                    result = await db.execute(
                        select(DBAuthor).where(DBAuthor.name.in_(all_author_names))
                    )
                    for author in result.scalars().all():
                        existing_authors[author.name] = author
                
                categories_to_create = all_category_names - existing_categories.keys()
                if categories_to_create:
                    category_objects = [DBCategory(name=name) for name in categories_to_create]
                    db.add_all(category_objects)
                    await db.flush()
                    
                    # Query again to get all categories
                    result = await db.execute(
                        select(DBCategory).where(DBCategory.name.in_(all_category_names))
                    )
                    for category in result.scalars().all():
                        existing_categories[category.name] = category
                
                # add papers and their associations
                for paper in papers_to_add:
                    db_paper = DBPaper(
                        paper_id=paper.paper_id,
                        title=paper.title,
                        abstract=paper.abstract,
                        pdf_url=paper.pdf_url,
                        published_date=paper.published_date,
                        updated_date=paper.updated_date,
                        click_count=0  # Initialize click count to 0 for new papers
                    )
                    
                    # Add category associations
                    for category_name in paper.categories:
                        db_paper.categories.append(existing_categories[category_name])
                    
                    db.add(db_paper)
                    await db.flush()  # Flush to get the paper_id
                    
                    # Add author associations with order using PostgreSQL's ON CONFLICT DO UPDATE
                    for order, author_name in enumerate(paper.authors):
                        await db.execute(
                            text("""
                                INSERT INTO paper_authors (paper_id, author, author_order) 
                                VALUES (:paper_id, :author, :author_order)
                                ON CONFLICT (paper_id, author) DO UPDATE SET
                                    author_order = EXCLUDED.author_order
                            """),
                            {
                                "paper_id": paper.paper_id,
                                "author": author_name,
                                "author_order": order
                            }
                        )
                    
                    added_ids.append(paper.paper_id)
                
                await db.commit()
                logger.info(f"Added {len(added_ids)} papers to the database")
                
            except Exception as e:
                await db.rollback()
                logger.error(f"Failed to add papers: {e}")
                raise
            
        return added_ids
    
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
                        pdf_url=db_paper.pdf_url,
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
        """
        get papers by a list of paper_ids
        """
        papers = []
        async for db in get_async_db():
            result = await db.execute(
                select(DBPaper)
                .options(
                    selectinload(DBPaper.authors),
                    selectinload(DBPaper.categories)
                )
                .where(DBPaper.paper_id.in_(paper_ids))
            )
            db_papers = result.scalars().all()
            
            for db_paper in db_papers:
                papers.append(Paper(
                    paper_id=db_paper.paper_id,
                    title=db_paper.title,
                    authors=[author.name for author in db_paper.authors],
                    abstract=db_paper.abstract,
                    categories=[category.name for category in db_paper.categories],
                    pdf_url=db_paper.pdf_url,
                    published_date=db_paper.published_date,
                    updated_date=db_paper.updated_date
                ))
        
        return papers
    
    async def get_recent_papers(self, limit: int = 30, offset: int = 0) -> List[Paper]:
        """
        get recent papers from database
        """
        papers = []
        async for db in get_async_db():
            result = await db.execute(
                select(DBPaper)
                .options(
                    selectinload(DBPaper.authors),
                    selectinload(DBPaper.categories)
                )
                .order_by(DBPaper.published_date.desc())
                .offset(offset)
                .limit(limit)
            )
            db_papers = result.scalars().all()
            
            for db_paper in db_papers:
                papers.append(Paper(
                    paper_id=db_paper.paper_id,
                    title=db_paper.title,
                    authors=[author.name for author in db_paper.authors],
                    abstract=db_paper.abstract,
                    categories=[category.name for category in db_paper.categories],
                    pdf_url=db_paper.pdf_url,
                    published_date=db_paper.published_date,
                    updated_date=db_paper.updated_date
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
                    select(DBUser.user_id).where(DBUser.email == email)
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

    async def add_session(self, session_id: str, user_id: int, session_time: datetime) -> bool:
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
                    select(DBUser).where(DBUser.user_id == user_id)
                )
                user = result.scalars().first()
                
                if not user:
                    logger.warning(f"User with ID {user_id} not found")
                    return False
                
                # Create new session with specified time
                new_session = DBSession(
                    session_id=session_id,
                    user_id=user_id,
                    created_at=session_time,
                    last_message_at=session_time
                )
                
                db.add(new_session)
                await db.commit()
                
                logger.info(f"Successfully created new session: {session_id} for user: {user_id} at {session_time}")
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
        if not session_id or not content or not role:
            logger.warning("empty session_id, content, or role")
            return False
            
        async for db in get_async_db():
            try:
                result = await db.execute(
                    select(DBSession).where(DBSession.session_id == session_id)
                )
                session = result.scalars().first()
                
                if not session:
                    logger.warning(f"Session {session_id} not found")
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

# Create a global instance
db_service = DBService() 