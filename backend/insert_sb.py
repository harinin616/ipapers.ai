#!/usr/bin/env python3
"""
Import embeddings from PostgreSQL into FAISS in large batches (no duplicates).
Safely rebuilds or updates the FAISS index from DBPaper.embedding column.
"""

import asyncio
import numpy as np
import logging
from sqlalchemy import select
from app.db.database import get_async_db
from app.models.db_models import DBPaper
from app.services.vector_search_service import vector_search_service
import time

# ----------------------------
# CONFIG
# ----------------------------
BATCH_SIZE = 20000    # Fetch 20,000 papers per PostgreSQL query
SAVE_EVERY = 1000000    # Intended to save every 20,000 papers (but see issue below)
# ----------------------------

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("db_to_faiss")

async def import_embeddings_from_db_to_faiss():
    total_added = 0
    batch_number = 1

    # Load already-indexed papers
    existing_keys = set(zip(vector_search_service.paper_ids, vector_search_service.paper_platforms))
    logger.info(f"🧩 Loaded {len(existing_keys)} already indexed papers from FAISS.")

    async for db in get_async_db():
        offset = 4000000
        while True:
            logger.info(f"📦 Fetching batch #{batch_number} (OFFSET {offset}, LIMIT {BATCH_SIZE})...")
            result = await db.execute(
                select(DBPaper.paper_id, DBPaper.embedding, DBPaper.platform)
                .order_by(DBPaper.paper_id)
                .offset(offset)
                .limit(BATCH_SIZE)
            )
            rows = result.all()
            if not rows:
                logger.info("✅ No more rows found — import complete.")
                break

            batch_embeddings = []
            batch_paper_ids = []
            batch_platforms = []

            for paper_id, emb, platform in rows:
                if emb is None:
                    continue

                key = (paper_id, platform)
                if key in existing_keys:
                    # Skip duplicates already in FAISS
                    continue

                try:
                    emb_np = np.array(emb, dtype="float32")
                    batch_embeddings.append(emb_np)
                    batch_paper_ids.append(paper_id)
                    batch_platforms.append(platform)
                    existing_keys.add(key)  # mark as indexed
                except Exception as e:
                    logger.warning(f"Skipping paper {paper_id}: invalid embedding ({e})")

            if not batch_embeddings:
                logger.warning(f"No new embeddings in batch #{batch_number}")
                offset += BATCH_SIZE
                batch_number += 1
                continue

            # Add new embeddings to FAISS
            vector_search_service.index.add(np.array(batch_embeddings))
            vector_search_service.paper_ids.extend(batch_paper_ids)
            vector_search_service.paper_platforms.extend(batch_platforms)

            total_added += len(batch_embeddings)
            logger.info(f"✅ Batch #{batch_number} added {len(batch_embeddings)} vectors (Total: {total_added})")
            # vector_search_service.save_index()  # or whatever your service uses internally
            # logger.info("💾 Saved FAISS index to disk after batch.")

            if offset % SAVE_EVERY == 0:
                logger.info(f"💾 Saving FAISS index after {offset} embeddings")
                vector_search_service.save_index()
                logger.info(f"💾 Saved FAISS index after {total_added} embeddings")

            offset += BATCH_SIZE
            batch_number += 1

        # Final save
        vector_search_service.save_index()
        await db.close()

    logger.info(f"🎉 Import complete! Total new embeddings added to FAISS: {total_added}")

if __name__ == "__main__":
    asyncio.run(import_embeddings_from_db_to_faiss())
