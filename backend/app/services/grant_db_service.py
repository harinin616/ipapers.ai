import logging
from typing import List, Optional
from sqlalchemy.future import select
from sqlalchemy import and_, or_
from sqlalchemy.exc import SQLAlchemyError

from app.models.grant import Grant
from app.models.db_models import DBGrant
from app.db.database import get_async_db
from app.services.llm_service import llm_service

logger = logging.getLogger(__name__)


class GrantDBService:
    async def add_grants(self, grants: List[Grant]) -> List[str]:
        if not grants:
            return []

        added_ids: List[str] = []

        async for db in get_async_db():
            try:
                incoming_ids = [g.grant_id for g in grants]
                existing = await db.execute(
                    select(DBGrant.grant_id).where(DBGrant.grant_id.in_(incoming_ids))
                )
                existing_ids = set(existing.scalars().all())

                to_add = [g for g in grants if g.grant_id not in existing_ids]
                if not to_add:
                    logger.info("All grants already exist, skipping insert.")
                    return []

                texts = [f"{g.title}\n\n{g.synopsis or ''}" for g in to_add]
                embeddings = await llm_service.get_embeddings(texts)
                if embeddings is None:
                    logger.warning("Embedding service returned None for grants; storing without embeddings.")
                    embeddings = [None] * len(to_add)

                for g, emb in zip(to_add, embeddings):
                    db_g = DBGrant(
                        grant_id=g.grant_id,
                        title=g.title,
                        agency=g.agency,
                        synopsis=g.synopsis,
                        detail_url=g.detail_url,
                        posted_date=g.posted_date,
                        updated_date=g.updated_date,
                        close_date=g.close_date,
                        status=g.status,
                        embedding=emb,
                    )
                    db.add(db_g)
                    added_ids.append(g.grant_id)

                await db.commit()
                logger.info(f"Inserted {len(added_ids)} grants (with embeddings where available).")

            except SQLAlchemyError:
                await db.rollback()
                logger.exception("DB error inserting grants")
                raise
            except Exception:
                await db.rollback()
                logger.exception("Unexpected error inserting grants")
                raise

        return added_ids

    async def get_grants_by_ids(self, grant_ids: List[str]) -> List:
        """Get grants by their IDs"""
        if not grant_ids:
            return []

        async for db in get_async_db():
            try:
                result = await db.execute(
                    select(DBGrant).where(DBGrant.grant_id.in_(grant_ids))
                )
                grants = result.scalars().all()
                return grants
            except Exception as e:
                logger.error(f"Error getting grants by IDs: {e}")
                return []

    async def search_grants_by_keywords(self, query: str, limit: int = 20) -> List[DBGrant]:
        """Search grants by simple keyword matching on title and synopsis."""
        normalized_query = (query or "").strip()
        if not normalized_query:
            return []

        like_pattern = f"%{normalized_query}%"

        async for db in get_async_db():
            try:
                result = await db.execute(
                    select(DBGrant)
                    .where(
                        or_(
                            DBGrant.title.ilike(like_pattern),
                            DBGrant.synopsis.ilike(like_pattern)
                        )
                    )
                    .limit(limit)
                )
                return result.scalars().all()
            except Exception:
                logger.exception("Error searching grants by keywords")
                return []


grant_db_service = GrantDBService()
