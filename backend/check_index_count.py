#!/usr/bin/env python3
"""
检查FAISS索引和数据库中的论文数量
"""

import os
import sys
import pickle
import faiss
import asyncio
import logging
from pathlib import Path
from sqlalchemy import func, select

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.append(str(project_root))

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# 导入数据库模型
from app.db.database import get_async_db
from app.models.db_models import DBPaper

async def check_paper_counts():
    """
    检查FAISS索引和数据库中的论文数量
    """
    # 1. 检查FAISS索引
    data_dir = project_root / "data"
    index_path = data_dir / "paper_index.faiss"
    paper_ids_path = data_dir / "paper_ids.pkl"
    
    # 检查索引文件是否存在
    if not index_path.exists() or not paper_ids_path.exists():
        logger.error(f"索引文件不存在: {index_path} 或 {paper_ids_path}")
        return
    
    # 加载FAISS索引
    try:
        index = faiss.read_index(str(index_path))
        logger.info(f"FAISS索引中包含 {index.ntotal} 个向量")
    except Exception as e:
        logger.error(f"读取FAISS索引出错: {e}")
        return
    
    # 加载paper_ids文件
    try:
        with open(paper_ids_path, 'rb') as f:
            loaded_data = pickle.load(f)
        
        # 检查是否为新格式（元组列表）
        if loaded_data and isinstance(loaded_data[0], tuple):
            # 新格式: [(paper_id, platform), ...]
            paper_ids = [item[0] for item in loaded_data]
            platforms = [item[1] for item in loaded_data]
            logger.info(f"Paper IDs文件中包含 {len(paper_ids)} 个ID，格式为元组列表")
            
            # 统计每个平台的论文数量
            platform_counts = {}
            for platform in platforms:
                platform_counts[platform] = platform_counts.get(platform, 0) + 1
                
            logger.info(f"按平台统计论文数量: {platform_counts}")
        else:
            # 旧格式: [paper_id, ...]
            paper_ids = loaded_data
            logger.info(f"Paper IDs文件中包含 {len(paper_ids)} 个ID，格式为旧格式")
        
        # 检查FAISS索引和paper_ids是否匹配
        if index.ntotal != len(paper_ids):
            logger.warning(f"警告: FAISS索引向量数量 ({index.ntotal}) 与paper_ids数量 ({len(paper_ids)}) 不匹配!")
    except Exception as e:
        logger.error(f"读取paper_ids文件出错: {e}")
        return
    
    # 2. 检查数据库中的论文数量
    try:
        async for db in get_async_db():
            # 统计数据库中的论文总数
            result = await db.execute(select(func.count()).select_from(DBPaper))
            db_paper_count = result.scalar()
            logger.info(f"数据库中共有 {db_paper_count} 篇论文")
            
            # 按平台统计数据库中的论文数量
            result = await db.execute(
                select(DBPaper.platform, func.count())
                .group_by(DBPaper.platform)
            )
            platform_counts = {platform: count for platform, count in result.all()}
            logger.info(f"数据库中按平台统计的论文数量: {platform_counts}")
            
            # 检查索引覆盖率
            coverage = len(paper_ids) / db_paper_count if db_paper_count > 0 else 0
            logger.info(f"索引覆盖率: {coverage:.2%} (索引中 {len(paper_ids)} / 数据库中 {db_paper_count})")
            
    except Exception as e:
        logger.error(f"查询数据库出错: {e}")
        return

async def main():
    await check_paper_counts()

if __name__ == "__main__":
    asyncio.run(main()) 