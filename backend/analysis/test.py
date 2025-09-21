#!/usr/bin/env python3
import os
import asyncio
import logging

from typing import List, Optional

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy import select, update, func, null

from app.models.db_models import DBPaper
from app.services.llm_service import llm_service  # 替换成你实际的 service 路径

# ---------- 配置区 ----------
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:yourpass@localhost:5432/dlmonitor"
)

LOG_LEVEL = logging.INFO
DB_FETCH_BATCH = 1000   # 每次从 DB 取多少条记录
# ----------------------------

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("generate_embeddings")


async def process_batch(session: AsyncSession, papers: List[DBPaper]):
    """
    对单个 batch 的 papers 生成 embeddings 并更新到数据库
    """
    texts = [f"{p.title}\n\n{p.abstract}" for p in papers]
    embs: Optional[List[List[float]]] = await llm_service.get_embeddings(texts)
    if embs is None:
        logger.error("llm_service.get_embeddings 返回 None，本 batch 跳过")
        return

    for paper, emb in zip(papers, embs):
        # 再次检查以防 race condition
        if paper.embedding is not None:
            continue

        await session.execute(
            update(DBPaper)
            .where(DBPaper.paper_id == paper.paper_id)
            .values(embedding=emb)
        )


async def main():
    engine = create_async_engine(DATABASE_URL, echo=False)
    AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with AsyncSessionLocal() as session:
        # 只统计 embedding 为空的记录数
        total = (
            await session.execute(
                select(func.count()).select_from(DBPaper)
                .where(DBPaper.embedding.is_(None))
            )
        ).scalar_one()
        logger.info(f"共有 {total} 篇论文 embedding 为空，需要生成 embedding")

        offset = 0
        while offset < total:
            # 分批取出 embedding 为空的 DBPaper 对象
            result = await session.execute(
                select(DBPaper)
                .where(DBPaper.embedding.is_(None))
                .order_by(DBPaper.paper_id)
                .limit(DB_FETCH_BATCH)
                .offset(offset)
            )
            batch = result.scalars().all()
            if not batch:
                break

            logger.info(f"处理第 {offset // DB_FETCH_BATCH + 1} 批（{len(batch)} 条）")
            await process_batch(session, batch)
            await session.commit()

            offset += len(batch)

    await engine.dispose()
    logger.info("所有论文 embedding 生成完毕")


if __name__ == "__main__":
    asyncio.run(main())
