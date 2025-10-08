# backend/app/services/keyword_search_service.py

from sqlalchemy.orm import Session
from sqlalchemy.sql import text
import logging
from app.services.conv_db_service import conv_db_service
import re
import sqlalchemy as sa
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.db_service import get_async_db
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)

class ConvKeywordSearchService:

    async def keyword_search(
            self,
            query: str,
            limit: int = 50,
            similarity_threshold: float = 0.3,  # 0.3 ~ ~90% similarity
        ) -> List[Tuple[str, str]]:
            """
            关键词检索，支持模糊匹配（pg_trgm similarity）
            """
            if not query or not query.strip():
                return []

            terms = re.split(r"\s+", query.strip())
            processed_query = " & ".join(t for t in terms if t)
            limit = max(1, min(int(limit), 1000))
            print(f"keyword_search: query='{query}', processed='{processed_query}', limit={limit}")

            async for db in get_async_db():  # type: AsyncSession
                try:
                    # 1️⃣ 尝试原 FTS
                    sql_to = sa.text("""
                        SELECT paper_id, platform
                        FROM papers
                        WHERE tsv @@ to_tsquery(:cfg, unaccent(:q))
                        ORDER BY ts_rank_cd(tsv, to_tsquery(:cfg, unaccent(:q))) DESC
                        LIMIT :lim
                    """)
                    res = await db.execute(sql_to, {"cfg": FTS_CONFIG, "q": processed_query, "lim": limit})
                    rows = res.fetchall()
                    if rows:
                        return [(row[0], row[1]) for row in rows]

                    # 2️⃣ fallback: pg_trgm similarity
                    sql_trgm = sa.text("""
                        SELECT paper_id, platform
                        FROM papers
                        WHERE similarity(title, :q) > :sim_thresh
                        ORDER BY similarity(title, :q) DESC
                        LIMIT :lim
                    """)
                    res = await db.execute(sql_trgm, {"q": query, "sim_thresh": similarity_threshold, "lim": limit})
                    rows = res.fetchall()
                    return [(row[0], row[1]) for row in rows]

                except SQLAlchemyError as e:
                    logger.error(f"DB error in keyword_search: {e}", exc_info=True)
                    return []
                except Exception as e:
                    logger.error("Unexpected error in keyword_search", exc_info=True)
                    return []

            return []




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