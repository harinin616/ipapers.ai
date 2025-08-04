import asyncio
from app.db.database import get_async_db
from app.services.db_service import db_service

async def get_paper():
    paper_id = "2308.07124"
    platform = "arxiv"
    print(f"Looking for paper_id: {paper_id}, platform: {platform}")
    
    # 使用数据库服务查询
    async for db in get_async_db():
        paper = await db_service.get_paper_by_id(paper_id, platform)
        if paper:
            print(f"Found paper: {paper}")
        else:
            print(f"Paper not found in database")
        break

if __name__ == "__main__":
    asyncio.run(get_paper()) 