# backend/app/services/keyword_search_service.py

from sqlalchemy.orm import Session
from sqlalchemy.sql import text
import logging
from app.services.conv_db_service import conv_db_service

logger = logging.getLogger(__name__)

class ConvKeywordSearchService:
    async def search(self, query: str, limit: int = 8000, allow_ids: set[tuple[str, str]] | None = None) -> list[tuple[str, str]]:
        """
        使用PostgreSQL FTS功能进行关键词搜索。
        
        这个函数是同步的，应该在FastAPI的线程池中运行。
        
        返回: 一个 (paper_id, platform) 元组的列表，按相关性排序。
        """
        logger.info(f"Executing keyword search for: '{query}'")
        if allow_ids:
            logger.info(f"Keyword search: allow_ids provided with {len(allow_ids)} entries")
        else:
            logger.info("Keyword search: no allow_ids provided, searching all papers")
        try:
            # 将用户查询字符串转换为PostgreSQL的tsquery格式 (e.g., 'deep learning' -> 'deep & learning')
            paper_id_platform_pairs = await conv_db_service.keyword_search(query=query, allow_ids=allow_ids)
            logger.info(f"Keyword search returned {len(paper_id_platform_pairs)} results")
            return paper_id_platform_pairs

        except Exception as e:
            logger.error(f"Error during keyword search in PostgreSQL: {e}", exc_info=True)
            # 向上抛出异常，让API层处理HTTP响应
            raise e

# 创建一个服务实例，以便在其他地方导入和使用
conv_keyword_search_service = ConvKeywordSearchService()