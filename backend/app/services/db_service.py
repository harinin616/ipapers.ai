import logging
from typing import List, Optional
from sqlalchemy.future import select
from sqlalchemy import func, insert, text
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError

from app.models.paper import Paper
from app.models.db_models import DBPaper, DBAuthor, DBCategory, paper_authors
from app.db.database import get_async_db

logger = logging.getLogger(__name__)

class DBService:
    """
    PostgreSQL database service to interact with database
    """
    
    def __init__(self):
        pass
    
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
                        updated_date=paper.updated_date
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
                        updated_date=db_paper.updated_date,
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
                    updated_date=db_paper.updated_date,
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

# Create a global instance
db_service = DBService() 