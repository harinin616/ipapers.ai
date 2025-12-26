import asyncio
from sqlalchemy import select
from app.db.database import get_async_db
from app.models.paper import Paper  # your SQLAlchemy model

async def get_arxiv_papers():
    print("Looking for papers with no '.' in paper_id and platform='arxiv'")
    
    async for db in get_async_db():
        stmt = select(Paper.__table__).where(
            Paper.__table__.c.platform == 'arxiv',
            ~Paper.__table__.c.paper_id.contains('.')
        )
        result = await db.execute(stmt)
        papers = result.fetchall()  # returns list of Row objects
        
        if papers:
            print(f"Found {len(papers)} papers:")
            for paper in papers:
                print(dict(paper))  # convert Row to dict
        else:
            print("No matching papers found")
        break

if __name__ == "__main__":
    asyncio.run(get_arxiv_papers())
