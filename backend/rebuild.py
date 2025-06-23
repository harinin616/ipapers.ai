# rebuild.py
from dotenv import load_dotenv, find_dotenv
load_dotenv(find_dotenv())   # ← 一定要最先执行

import asyncio
import os
import logging

from app.services.vector_search_service import vector_search_service
from app.services.db_service import db_service

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

BATCH_SIZE = 1  # 每次处理多少篇论文

async def main():
    # 1. 删除旧索引文件（可选）
    try:
        os.remove(vector_search_service.index_path)
        os.remove(vector_search_service.paper_ids_path)
        logger.info("Old index files removed.")
    except FileNotFoundError:
        logger.info("No existing index files to remove.")

    # 2. 重新加载（会自动创建空索引）
    vector_search_service.load_index()
    logger.info("Created new empty FAISS index.")

    # 3. 从数据库取出所有论文 ID 列表
    all_papers = await db_service.get_all_papers()
    total = len(all_papers)
    logger.info(f"Fetched {total} papers from database.")

    # 4. 分批添加到索引
    for start in range(0, total, BATCH_SIZE):
        end = min(start + BATCH_SIZE, total)
        batch = all_papers[start:end]
        logger.info(f"Indexing papers {start+1}–{end} / {total} ...")
        await vector_search_service.add_papers(batch)
        print(f"Indexed papers {start+1}–{end} / {total}")
    logger.info("Index rebuild complete.")

if __name__ == "__main__":
    asyncio.run(main())
