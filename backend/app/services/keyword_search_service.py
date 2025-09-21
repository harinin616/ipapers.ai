# backend/app/services/keyword_search_service.py

from sqlalchemy.orm import Session
from sqlalchemy.sql import text
import logging
from app.services.db_service import db_service

logger = logging.getLogger(__name__)

class KeywordSearchService:
    async def search(self, query: str, limit: int = 20) -> list[tuple[str, str]]:
        """
        使用PostgreSQL FTS功能进行关键词搜索。
        
        这个函数是同步的，应该在FastAPI的线程池中运行。
        
        返回: 一个 (paper_id, platform) 元组的列表，按相关性排序。
        """
        logger.info(f"Executing keyword search for: '{query}'")
        try:
            # 将用户查询字符串转换为PostgreSQL的tsquery格式 (e.g., 'deep learning' -> 'deep & learning')
            print(f"query={query}")
            paper_id_platform_pairs = await db_service.keyword_search(query=query)
            print(f"keyword_search_service: {paper_id_platform_pairs}")
            return paper_id_platform_pairs

        except Exception as e:
            logger.error(f"Error during keyword search in PostgreSQL: {e}", exc_info=True)
            # 向上抛出异常，让API层处理HTTP响应
            raise e

# 创建一个服务实例，以便在其他地方导入和使用
keyword_search_service = KeywordSearchService()