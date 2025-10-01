import asyncio
from app.db.database import get_async_db
from app.services.db_service import db_service

async def get_paper():
    paper_id = "39399407"
    print(f"Looking for paper_id: {paper_id}")
    
    async for db in get_async_db():
        paper = await db_service.get_paper_by_id(paper_id)  # no platform
        if paper:
            published_date = getattr(paper, "published_date", None)
            updated_date = getattr(paper, "updated_date", None)

            print(f"✅ Found paper {paper_id}")
            print(f"   Published Date: {published_date}")
            print(f"   Updated Date:   {updated_date}")
        else:
            print(f"⚠️ Paper not found in database")
        break

if __name__ == "__main__":
    asyncio.run(get_paper())
