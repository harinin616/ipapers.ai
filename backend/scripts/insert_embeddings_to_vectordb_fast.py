#!/usr/bin/env python3
"""
Sync PostgreSQL papers to FAISS Vector Database

This script syncs papers from PostgreSQL to FAISS by:
1. Finding papers that exist in PostgreSQL but not in FAISS
2. Adding those papers to FAISS using their pre-computed embeddings
"""

import os
import sys
import asyncio
import argparse
import numpy as np

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.future import select
from sqlalchemy import func, and_
from app.models.db_models import DBPaper, DBAuthor, DBCategory, paper_authors, paper_categories
from app.db.database import get_async_db
from app.models.paper import Paper
from app.services.vector_search_service import vector_search_service


async def sync_db_to_faiss(max_papers_to_add=None, batch_size=100):
    """
    Add missing papers from PostgreSQL to FAISS
    
    Args:
        max_papers_to_add: Maximum number of papers to add (None = add all)
        batch_size: Number of papers to process per batch
    """
    
    print("Starting sync: PostgreSQL -> FAISS")
    
    # Step 1: Reload FAISS index in writable mode (default is read-only)
    vector_search_service.reload_writable()
    print(f"Loaded FAISS index: {vector_search_service.index.ntotal:,} vectors")
    
    # Step 2: Get list of papers already in FAISS to avoid duplicates
    existing_in_faiss = set(
        (paper_id, platform) 
        for paper_id, platform in zip(
            vector_search_service.paper_ids, 
            vector_search_service.paper_platforms
        )
    )
    
    # Step 3: Query PostgreSQL and find papers not in FAISS
    print(f"Scanning PostgreSQL database (batch size: {batch_size})...")
    
    papers_to_add = []
    embeddings_to_add = []
    papers_without_embeddings = []
    offset = 0
    
    async for db in get_async_db():
        while True:
            # Query papers with their authors and categories
            stmt = (
                select(
                    DBPaper,
                    func.array_agg(func.distinct(DBAuthor.name)).label("authors"),
                    func.array_agg(func.distinct(DBCategory.name)).label("categories")
                )
                .outerjoin(paper_authors, and_(
                    paper_authors.c.paper_id == DBPaper.paper_id,
                    paper_authors.c.platform == DBPaper.platform
                ))
                .outerjoin(DBAuthor, paper_authors.c.author == DBAuthor.name)
                .outerjoin(paper_categories, and_(
                    paper_categories.c.paper_id == DBPaper.paper_id,
                    paper_categories.c.platform == DBPaper.platform
                ))
                .outerjoin(DBCategory, paper_categories.c.category == DBCategory.name)
                .group_by(DBPaper)
                .limit(batch_size)
                .offset(offset)
            )
            
            result = await db.execute(stmt)
            batch = result.all()
            
            if not batch:
                break  # No more papers in database
            
            # Process each paper in the batch
            for record in batch:
                db_paper = record[0]
                authors = record[1] if record[1] and record[1][0] is not None else []
                categories = record[2] if record[2] and record[2][0] is not None else []
                
                # Skip if paper already exists in FAISS
                if (db_paper.paper_id, db_paper.platform) in existing_in_faiss:
                    continue
                
                # Convert to Paper object
                paper = Paper(
                    paper_id=db_paper.paper_id,
                    platform=db_paper.platform,
                    title=db_paper.title,
                    abstract=db_paper.abstract,
                    pdf_url=db_paper.pdf_url,
                    published_date=db_paper.published_date,
                    updated_date=db_paper.updated_date,
                    authors=authors,
                    categories=categories
                )
                
                # Check if paper has embedding
                if db_paper.embedding is not None:
                    papers_to_add.append(paper)
                    embeddings_to_add.append(np.array(db_paper.embedding, dtype='float32'))
                else:
                    papers_without_embeddings.append((db_paper.paper_id, db_paper.platform))
                
                # Stop if we hit the limit
                if max_papers_to_add is not None and len(papers_to_add) >= max_papers_to_add:
                    break
            
            # Progress update
            if len(papers_to_add) % 500 == 0 and len(papers_to_add) > 0:
                print(f"  Found {len(papers_to_add):,} papers to add...")
            
            # Stop if we hit the limit
            if max_papers_to_add is not None and len(papers_to_add) >= max_papers_to_add:
                break
            
            offset += batch_size
    
    # Summary of what we found
    print(f"Found {len(papers_to_add):,} papers with embeddings to add to FAISS")
    
    if papers_without_embeddings:
        print(f"WARNING: {len(papers_without_embeddings):,} papers missing embeddings (will be skipped)")
        if len(papers_without_embeddings) <= 5:
            for paper_id, platform in papers_without_embeddings:
                print(f"  - {paper_id} ({platform})")
    
    # Exit early if nothing to add
    if not papers_to_add:
        print("FAISS is already in sync with PostgreSQL")
        return
    
    # Step 4: Add all papers to FAISS in one shot
    print(f"Adding {len(papers_to_add):,} papers to FAISS in one shot...")
    await vector_search_service.add_papers_with_embeddings(papers_to_add, embeddings_to_add, save_index=False)
    print(f"  Successfully added {len(papers_to_add):,} papers to FAISS index")
    
    # Step 5: Save index once at the end
    print(f"Saving index to disk...")
    vector_search_service.save_index()
    
    # Final summary
    print(f"\nSync complete!")
    print(f"  Papers added: {len(papers_to_add):,}")
    print(f"  Total in FAISS: {vector_search_service.index.ntotal:,}")
    print(f"\nNote: Restart web service to load the updated index")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Sync PostgreSQL papers to FAISS vector database using vector_search_service",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--max', '-m',
        type=int,
        default=None,
        help='Maximum number of papers to add (default: no limit, add all missing papers)'
    )
    
    parser.add_argument(
        '--batch-size', '-b',
        type=int,
        default=100,
        help='Number of papers to process per batch (default: 100)'
    )
    
    args = parser.parse_args()
    
    asyncio.run(sync_db_to_faiss(max_papers_to_add=args.max, batch_size=args.batch_size))
