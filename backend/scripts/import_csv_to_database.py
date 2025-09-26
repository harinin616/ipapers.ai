#!/usr/bin/env python3
"""
CSV Database Importer with Dual Embeddings (Batch Mode)

Imports papers from CSV with pre-computed embeddings into:
1. PostgreSQL database (db_embedding column)
2. FAISS vector search index (vector_embedding column)

Processes papers in batches of 100 to improve performance for large CSVs.
"""

import os
import sys
import asyncio
import logging
import csv
import ast
import numpy as np
from datetime import datetime
from typing import List, Optional
import argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BATCH_SIZE = 100  # Process 100 papers at a time

# --- Import services if available ---
try:
    from app.services.db_service import db_service
    from app.services.vector_search_service import vector_search_service
    from app.models.paper import Paper
    SERVICES_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Some services not available: {e}. Running in CSV-only mode.")
    SERVICES_AVAILABLE = False

    class Paper:
        def __init__(self, paper_id, title, authors, abstract, categories=None, pdf_url="", published_date=None, updated_date=None, platform="pubmed"):
            self.paper_id = paper_id
            self.title = title
            self.authors = authors
            self.abstract = abstract
            self.categories = categories or []
            self.pdf_url = pdf_url
            self.published_date = published_date
            self.updated_date = updated_date
            self.platform = platform

# --- Helper functions ---
def parse_embedding_from_string(embedding_str: str) -> List[float]:
    try:
        embedding_list = ast.literal_eval(embedding_str.strip())
        if isinstance(embedding_list, list) and all(isinstance(x, (int, float)) for x in embedding_list):
            return embedding_list
        else:
            return []
    except Exception as e:
        logger.warning(f"Failed to parse embedding string: {e}")
        return []

def read_papers_from_csv_with_dual_embeddings(csv_file_path: str):
    papers = []
    db_embeddings = []
    vector_embeddings = []

    try:
        with open(csv_file_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row_num, row in enumerate(reader, 1):
                try:
                    authors_str = row.get('authors', '')
                    try:
                        authors = ast.literal_eval(authors_str) if authors_str else []
                        if not isinstance(authors, list):
                            authors = [str(authors)]
                    except Exception:
                        authors = [authors_str] if authors_str else []

                    published_date = datetime.strptime(row['published_date'], '%Y-%m-%d').date()
                    updated_date = datetime.strptime(row['updated_date'], '%Y-%m-%d').date()

                    db_embedding = None
                    if row.get('db_embedding'):
                        db_emb_list = parse_embedding_from_string(row['db_embedding'])
                        if db_emb_list:
                            db_embedding = np.array(db_emb_list, dtype='float32')

                    vector_embedding = None
                    if row.get('vector_embedding'):
                        vec_emb_list = parse_embedding_from_string(row['vector_embedding'])
                        if vec_emb_list:
                            vector_embedding = np.array(vec_emb_list, dtype='float32')

                    paper = Paper(
                        paper_id=row['paper_id'],
                        title=row['title'],
                        authors=authors,
                        abstract=row['abstract'],
                        categories=['medical'],
                        pdf_url=row['pdf_url'],
                        published_date=published_date,
                        updated_date=updated_date,
                        platform="pubmed"
                    )

                    papers.append(paper)
                    db_embeddings.append(db_embedding)
                    vector_embeddings.append(vector_embedding)

                except Exception as e:
                    logger.error(f"Error parsing row {row_num}: {e}")
                    continue
        logger.info(f"Successfully read {len(papers)} papers from CSV file with dual embeddings")
        return papers, db_embeddings, vector_embeddings
    except Exception as e:
        logger.error(f"Failed to read CSV file {csv_file_path}: {e}", exc_info=True)
        return [], [], []

# --- Database insertion with batch logging ---
async def add_papers_to_database_with_precomputed_embeddings(papers: List[Paper], db_embeddings: List[np.ndarray], platform: str = "pubmed") -> List[str]:
    if not papers:
        return []

    added_ids = []

    from sqlalchemy.future import select
    from sqlalchemy import and_, text
    from sqlalchemy.exc import SQLAlchemyError, IntegrityError
    from app.models.db_models import DBPaper, DBAuthor, DBCategory
    from app.db.database import get_async_db

    async for db in get_async_db():
        try:
            incoming_ids = [p.paper_id for p in papers]
            result = await db.execute(
                select(DBPaper.paper_id)
                .where(
                    and_(
                        DBPaper.paper_id.in_(incoming_ids),
                        DBPaper.platform == platform
                    )
                )
            )
            existing_ids = set(result.scalars().all())
            papers_to_add = [p for p in papers if p.paper_id not in existing_ids]

            if not papers_to_add:
                return []

            # Process in batches
            for batch_start in range(0, len(papers_to_add), BATCH_SIZE):
                batch = papers_to_add[batch_start: batch_start + BATCH_SIZE]
                batch_embeddings = []
                batch_papers = []

                for p in batch:
                    db_emb = next((db_embeddings[i] for i, paper in enumerate(papers) if paper.paper_id == p.paper_id), None)
                    if db_emb is not None:
                        batch_embeddings.append(db_emb)
                        batch_papers.append(p)

                if not batch_papers:
                    continue

                # --- Sync authors ---
                all_authors = {a for p in batch_papers for a in p.authors}
                existing_authors = {}
                if all_authors:
                    res = await db.execute(select(DBAuthor).where(DBAuthor.name.in_(all_authors)))
                    for a in res.scalars().all():
                        existing_authors[a.name] = a
                    to_create = all_authors - existing_authors.keys()
                    if to_create:
                        db.add_all([DBAuthor(name=n) for n in to_create])
                        await db.flush()
                        res = await db.execute(select(DBAuthor).where(DBAuthor.name.in_(all_authors)))
                        for a in res.scalars().all():
                            existing_authors[a.name] = a

                # --- Sync categories ---
                all_cats = {c for p in batch_papers for c in p.categories}
                existing_cats = {}
                if all_cats:
                    res = await db.execute(select(DBCategory).where(DBCategory.name.in_(all_cats)))
                    for c in res.scalars().all():
                        existing_cats[c.name] = c
                    to_create = all_cats - existing_cats.keys()
                    if to_create:
                        db.add_all([DBCategory(name=n) for n in to_create])
                        await db.flush()
                        res = await db.execute(select(DBCategory).where(DBCategory.name.in_(all_cats)))
                        for c in res.scalars().all():
                            existing_cats[c.name] = c

                # --- Insert papers ---
                for p, emb in zip(batch_papers, batch_embeddings):
                    paper_platform = "pubmed"
                    check_result = await db.execute(
                        select(DBPaper.paper_id)
                        .where(
                            and_(
                                DBPaper.paper_id == p.paper_id,
                                DBPaper.platform == paper_platform
                            )
                        )
                    )
                    if check_result.scalar_one_or_none():
                        continue

                    db_p = DBPaper(
                        paper_id=p.paper_id,
                        title=p.title,
                        abstract=p.abstract,
                        pdf_url=p.pdf_url.replace("http://", "https://"),
                        published_date=p.published_date,
                        updated_date=p.updated_date,
                        click_count=0,
                        embedding=emb,
                        platform=paper_platform
                    )

                    for cat in p.categories:
                        db_p.categories.append(existing_cats[cat])

                    db.add(db_p)
                    await db.flush()

                    for order, name in enumerate(p.authors):
                        try:
                            check_result = await db.execute(
                                text("""
                                SELECT 1 FROM paper_authors WHERE paper_id=:pid AND author=:auth LIMIT 1
                                """),
                                {"pid": p.paper_id, "auth": name}
                            )
                            exists = check_result.scalar() is not None
                            if not exists:
                                await db.execute(
                                    text("""
                                    INSERT INTO paper_authors (paper_id, author, author_order, platform)
                                    VALUES (:pid, :auth, :ord, :platform)
                                    """),
                                    {"pid": p.paper_id, "auth": name, "ord": order, "platform": paper_platform}
                                )
                        except Exception as e:
                            logger.warning(f"Error inserting author {name} for paper {p.paper_id}: {e}")

                    added_ids.append(p.paper_id)

                await db.commit()
                logger.info(f"Database batch saved: papers {batch_start + 1}-{batch_start + len(batch_papers)}")

        except Exception as e:
            await db.rollback()
            logger.error(f"Database batch insert error: {e}", exc_info=True)
            raise

    return added_ids

# --- Vector search insertion with batch logging ---
async def add_papers_to_vector_search_with_precomputed_embeddings(papers: List[Paper], vector_embeddings: List[np.ndarray]) -> bool:
    if not papers:
        return True

    try:
        processed_keys = set((paper_id, platform) for paper_id, platform in zip(vector_search_service.paper_ids, vector_search_service.paper_platforms))

        for batch_start in range(0, len(papers), BATCH_SIZE):
            batch = papers[batch_start: batch_start + BATCH_SIZE]
            batch_embeddings = []
            batch_paper_ids = []
            batch_platforms = []

            for i, paper in enumerate(batch):
                platform = getattr(paper, 'platform', 'pubmed')
                key = (paper.paper_id, platform)
                if key not in processed_keys and vector_embeddings[i] is not None:
                    batch_embeddings.append(vector_embeddings[i])
                    batch_paper_ids.append(paper.paper_id)
                    batch_platforms.append(platform)
                else:
                    logger.info(f"Skipping paper {paper.paper_id} for vector index (duplicate or no embedding)")

            if not batch_embeddings:
                continue

            vector_search_service.index.add(np.array(batch_embeddings, dtype='float32'))
            vector_search_service.paper_ids.extend(batch_paper_ids)
            vector_search_service.paper_platforms.extend(batch_platforms)
            vector_search_service.save_index()

            logger.info(f"Vector search batch saved: papers {batch_start + 1}-{batch_start + len(batch_embeddings)}")

        return True
    except Exception as e:
        logger.error(f"Vector search batch insert error: {e}", exc_info=True)
        return False

# --- Save paper IDs ---
def save_paper_ids(paper_ids, data_dir):
    try:
        os.makedirs(data_dir, exist_ok=True)
        file_path = os.path.join(data_dir, 'latest_paper_ids.txt')
        with open(file_path, 'w', encoding='utf-8') as f:
            for pid in paper_ids:
                f.write(f"{pid}\n")
        logger.info(f"Saved {len(paper_ids)} paper IDs to {file_path}")
    except Exception as e:
        logger.error(f"Failed to save paper IDs: {e}", exc_info=True)

# --- Main ---
async def main(csv_file_path: str):
    platform = "pubmed"

    logger.info("=" * 80)
    logger.info("=" * 80)
    logger.info(f"Input CSV: {csv_file_path}")
    logger.info(f"Platform: {platform}")

    if not os.path.exists(csv_file_path):
        logger.error(f"CSV file not found: {csv_file_path}")
        return False

    papers, db_embeddings, vector_embeddings = read_papers_from_csv_with_dual_embeddings(csv_file_path)
    if not papers:
        return False

    papers_with_db = sum(1 for e in db_embeddings if e is not None)
    papers_with_vector = sum(1 for e in vector_embeddings if e is not None)
    logger.info(f"Papers with DB embeddings: {papers_with_db}/{len(papers)}")
    logger.info(f"Papers with Vector embeddings: {papers_with_vector}/{len(papers)}")

    added_ids = []

    if SERVICES_AVAILABLE:
        added_ids = await add_papers_to_database_with_precomputed_embeddings(papers, db_embeddings, platform)
        if added_ids:
            new_papers = [p for p in papers if p.paper_id in added_ids]
            new_vector_embeddings = [vector_embeddings[i] for i, p in enumerate(papers) if p.paper_id in added_ids]
            await add_papers_to_vector_search_with_precomputed_embeddings(new_papers, new_vector_embeddings)

    if added_ids:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.join(script_dir, '..', 'data')
        save_paper_ids(added_ids, data_dir)

    logger.info(f"Processed {len(papers)} papers, added to DB: {len(added_ids)} new papers.")
    
    
    
    log_csv_path = "import_log.csv"  # change path if needed

    # Check if file exists to write header
    file_exists = os.path.exists(log_csv_path)


    try:
        with open(log_csv_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["file_name", "number_of_papers"])  # header
            writer.writerow([os.path.basename(csv_file_path), len(added_ids)])
    except Exception as e:
        logger.error(f"Failed to append to log CSV: {e}")
        
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import CSV with dual embeddings into DB and vector index.")
    parser.add_argument("csv_file", help="Path to the CSV file containing papers with embeddings")
    args = parser.parse_args()

    success = asyncio.run(main(args.csv_file))
    if not success:
        sys.exit(1)
    sys.exit(0)
