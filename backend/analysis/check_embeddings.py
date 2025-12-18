#!/usr/bin/env python3
import os
import asyncio
import logging

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.db_models import DBPaper

# 配置区：修改为你的连接串或设置环境变量 DATABASE_URL
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:yourpass@localhost:5432/dlmonitor"
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("count_null_embeddings")


async def main():
    # 创建异步引擎
    engine = create_async_engine(DATABASE_URL, echo=False)
    AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with AsyncSessionLocal() as session:
        # 查询 embedding 为 NULL 的数量
        result_null = await session.execute(
            select(func.count()).select_from(DBPaper).where(DBPaper.embedding.is_(None))
        )
        null_count = result_null.scalar_one()

        # 查询 embedding 非 NULL 的数量
        result_filled = await session.execute(
            select(func.count()).select_from(DBPaper).where(DBPaper.embedding.is_not(None))
        )
        filled_count = result_filled.scalar_one()

        logger.info(f"Embeddings NULL: {null_count}")
        logger.info(f"Embeddings NOT NULL: {filled_count}")

        print(f"Embeddings NULL: {null_count}")
        print(f"Embeddings NOT NULL: {filled_count}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
