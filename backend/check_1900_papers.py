import asyncio
from sqlalchemy import select, extract
from app.db.database import get_async_db
from app.models.db_models import DBPaper

async def get_1900_pubmed_papers():
    platform = "pubmed"
    year_filter = 1900

    async for db in get_async_db():
        query = select(DBPaper).where(
            DBPaper.platform == platform,
            extract('year', DBPaper.published_date) == year_filter
        )
        result = await db.execute(query)
        papers = result.scalars().all()

        if papers:
            print(f"Found {len(papers)} papers with platform='{platform}' and published_date in {year_filter}:")
            for p in papers:
                print(f"- {p.paper_id} | {p.title} | {p.published_date}")
        else:
            print(f"No papers found with platform='{platform}' and published_date in {year_filter}")

if __name__ == "__main__":
    asyncio.run(get_1900_pubmed_papers())
