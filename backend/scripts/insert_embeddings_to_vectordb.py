#!/usr/bin/env python3
"""
Sync PostgreSQL papers to FAISS Vector Database
Uses vector_search_service to add papers that don't exist in FAISS yet
"""

import os
import sys
import asyncio
import argparse

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.future import select
from sqlalchemy import func, and_
from app.models.db_models import DBPaper, DBAuthor, DBCategory, paper_authors, paper_categories
from app.db.database import get_async_db
from app.models.paper import Paper
from app.services.vector_search_service import vector_search_service
import faiss


async def sync_db_to_faiss(max_papers_to_add=None, batch_size=100):
    """Add missing papers from PostgreSQL to FAISS using vector_search_service"""
    
    print("=" * 80)
    print("SYNC DATABASE TO FAISS VECTOR INDEX")
    print("=" * 80)
    
    # IMPORTANT: Reload the index in WRITABLE mode (not read-only)
    # The vector_search_service loads it as read-only by default
    print("\n" + "=" * 80)
    print("RELOADING INDEX IN WRITABLE MODE...")
    print("=" * 80)
    
    # if os.path.exists(vector_search_service.index_path):
    #     # Reload index WITHOUT read-only flag
    #     vector_search_service.index = faiss.read_index(vector_search_service.index_path)
    #     print(f"✓ Reloaded FAISS index in writable mode: {vector_search_service.index.ntotal:,} vectors")
    # else:
    #     print("✓ No existing index found, will create new one")
        
    vector_search_service.reload_writable()
    print(f"✓ Reloaded FAISS index in writable mode: {vector_search_service.index.ntotal:,} vectors")
    
    # Get existing papers in FAISS
    existing_in_faiss = set(
        (paper_id, platform) 
        for paper_id, platform in zip(
            vector_search_service.paper_ids, 
            vector_search_service.paper_platforms
        )
    )
    print(f"✓ Existing papers in FAISS: {len(existing_in_faiss):,}")
    
    # Query PostgreSQL for papers
    print("\n" + "=" * 80)
    print("QUERYING POSTGRESQL DATABASE...")
    print("=" * 80)
    
    async for db in get_async_db():
        # Count total papers in database
        result = await db.execute(
            select(func.count(DBPaper.paper_id))
        )
        total_in_db = result.scalar()
        print(f"✓ Total papers in PostgreSQL: {total_in_db:,}")
        
        if max_papers_to_add is None:
            print(f"✓ Limit: No limit - will add ALL missing papers")
        else:
            print(f"✓ Limit: Will add maximum {max_papers_to_add:,} papers this run")
        print(f"✓ Query batch size: {batch_size:,} papers per query")
        
        print("\n" + "=" * 80)
        print("STEP 1: FINDING PAPERS NOT IN FAISS...")
        print("=" * 80)
        
        # Query papers in batches and collect those missing from FAISS
        offset = 0
        papers_to_add = []
        total_checked = 0
        
        while True:
            # Query batch with full paper details (including authors and categories)
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
                break  # No more papers
            
            total_checked += len(batch)
            
            # Convert to Paper objects and check if missing from FAISS
            for record in batch:
                db_paper = record[0]
                authors = record[1] if record[1] and record[1][0] is not None else []
                categories = record[2] if record[2] and record[2][0] is not None else []
                
                # Check if this paper is missing from FAISS
                if (db_paper.paper_id, db_paper.platform) not in existing_in_faiss:
                    # Convert DBPaper to Paper object
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
                    papers_to_add.append(paper)
                    
                    # Check if we've hit the limit
                    if max_papers_to_add is not None and len(papers_to_add) >= max_papers_to_add:
                        print(f"  ✓ Reached limit of {max_papers_to_add:,} papers")
                        break
            
            print(f"  ✓ Checked {total_checked:,} papers | Found {len(papers_to_add):,} missing from FAISS")
            
            # Stop if we've hit the limit
            if max_papers_to_add is not None and len(papers_to_add) >= max_papers_to_add:
                break
            
            offset += batch_size
        
        print(f"✓ Total papers checked: {total_checked:,}")
        print(f"✓ Papers missing from FAISS: {len(papers_to_add):,}")
    
    # Database connection closed here
    
    if not papers_to_add:
        print("\n✓ No missing papers found! FAISS is already in sync.")
        return
    
    # Add papers using vector_search_service
    print("\n" + "=" * 80)
    print("STEP 2: ADDING PAPERS TO FAISS USING VECTOR SEARCH SERVICE...")
    print("=" * 80)
    print(f"Note: vector_search_service will generate embeddings from paper text/abstract")
    print(f"      and automatically save the index after adding papers.")
    
    # Process in batches to avoid memory issues
    total_added = 0
    for i in range(0, len(papers_to_add), batch_size):
        batch_end = min(i + batch_size, len(papers_to_add))
        batch = papers_to_add[i:batch_end]
        
        # Use vector_search_service to add papers
        await vector_search_service.add_papers(batch)
        
        total_added += len(batch)
        print(f"  ✓ Batch {i+1:,}-{batch_end:,} ({len(batch):,} papers) added | Total added: {total_added:,}")
    
    # Final statistics
    print("\n" + "=" * 80)
    print("SYNC COMPLETE")
    print("=" * 80)
    print(f"Papers in FAISS (before): {len(existing_in_faiss):,}")
    print(f"Papers added: {len(papers_to_add):,}")
    print(f"Papers in FAISS (after): {vector_search_service.index.ntotal:,}")
    print("=" * 80)
    print("\n⚠️  IMPORTANT: If your web service is running, restart it to load the updated index.")
    print("=" * 80)


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
