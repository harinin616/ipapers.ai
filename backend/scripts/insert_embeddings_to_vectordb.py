#!/usr/bin/env python3
"""
Sync PostgreSQL embeddings to FAISS
Adds papers from PostgreSQL that don't exist in FAISS yet
"""

import os
import sys
import asyncio
import pickle
import numpy as np
import argparse

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def sync_db_to_faiss(max_papers_to_add=None, batch_size=1000):
    """Add missing papers from PostgreSQL to FAISS"""
    from sqlalchemy.future import select
    from sqlalchemy import func
    from app.models.db_models import DBPaper
    from app.db.database import get_async_db
    import faiss
    
    data_dir = "/home/ec2-user/PMo/backend/data"
    index_path = os.path.join(data_dir, "paper_index.faiss")
    ids_path = os.path.join(data_dir, "paper_ids.pkl")
    platforms_path = os.path.join(data_dir, "paper_platforms.pkl")
    
    print("=" * 80)
    print("LOADING EXISTING FAISS DATA...")
    print("=" * 80)
    
    # Load existing FAISS index
    index = faiss.read_index(index_path)
    print(f"✓ Loaded FAISS index: {index.ntotal:,} vectors")

    # Load existing paper IDs and platforms
    with open(ids_path, 'rb') as f:
        paper_ids = pickle.load(f)
    print(f"✓ Loaded paper IDs: {len(paper_ids):,}")
    
    with open(platforms_path, 'rb') as f:
        platforms = pickle.load(f)
    print(f"✓ Loaded platforms: {len(platforms):,}")
    
    # Create set of existing papers in FAISS
    existing_in_faiss = set(zip(paper_ids, platforms))
    print(f"✓ Existing papers in FAISS: {len(existing_in_faiss):,}")
    
    # Query PostgreSQL for papers with embeddings
    print("\n" + "=" * 80)
    print("QUERYING POSTGRESQL DATABASE...")
    print("=" * 80)
    
    # Query database to get all papers
    async for db in get_async_db():
        # Count total papers with embeddings
        result = await db.execute(
            select(func.count(DBPaper.paper_id))
            .where(DBPaper.embedding.isnot(None))
        )
        total_in_db = result.scalar()
        print(f"✓ Total papers with embeddings in PostgreSQL: {total_in_db:,}")
        
        print(f"✓ Limit: Will add maximum {max_papers_to_add:,} papers this run")
        print(f"✓ Batch size: {batch_size:,} papers per batch")
        
        print("\n" + "=" * 80)
        print("STEP 1: QUERYING ALL PAPERS FROM POSTGRESQL...")
        print("=" * 80)
        
        # Query ALL papers from database
        result = await db.execute(
            select(DBPaper.paper_id, DBPaper.platform, DBPaper.embedding)
            .where(DBPaper.embedding.isnot(None))
        )
        all_papers = result.all()
        print(f"✓ Retrieved {len(all_papers):,} papers from PostgreSQL")
    
    # Database connection closed here - no longer needed
    
    print("\n" + "=" * 80)
    print("STEP 2: FILTERING PAPERS NOT IN FAISS...")
    print("=" * 80)
    
    # Build list of papers NOT in FAISS
    missing_papers = []
    for paper_id, platform, embedding in all_papers:
        if (paper_id, platform) not in existing_in_faiss:
            missing_papers.append((paper_id, platform, embedding))
            if len(missing_papers) >= max_papers_to_add:
                break
    
    print(f"✓ Found {len(missing_papers):,} papers missing from FAISS")
    print(f"✓ Will add {min(len(missing_papers), max_papers_to_add):,} papers")
    
    if not missing_papers:
        print("✓ No missing papers found! FAISS is already in sync.")
        return
    
    # Insert missing papers in batches
    print("\n" + "=" * 80)
    print("STEP 3: INSERTING PAPERS TO FAISS...")
    print("=" * 80)
    
    for i in range(0, len(missing_papers), batch_size):
        batch_end = min(i + batch_size, len(missing_papers))
        batch = missing_papers[i:batch_end]
        
        # Extract data
        batch_ids = [p[0] for p in batch]
        batch_platforms = [p[1] for p in batch]
        batch_embeddings = np.array([p[2] for p in batch], dtype='float32')
        
        # Add to FAISS
        index.add(batch_embeddings)
        paper_ids.extend(batch_ids)
        platforms.extend(batch_platforms)
        
        # Save after every batch
        faiss.write_index(index, index_path)
        with open(ids_path, 'wb') as f:
            pickle.dump(paper_ids, f)
        with open(platforms_path, 'wb') as f:
            pickle.dump(platforms, f)
        
        print(f"  ✓ Batch {i+1:,}-{batch_end:,} ({len(batch):,} papers) inserted & saved | Total: {index.ntotal:,}")
    
    added_count = len(missing_papers)
    
    # Final statistics
    print("\n" + "=" * 80)
    print("SYNC COMPLETE")
    print("=" * 80)
    print(f"Papers in FAISS (before): {index.ntotal - added_count:,}")
    print(f"Papers added: {added_count:,}")
    print(f"Papers in FAISS (after): {index.ntotal:,}")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Sync PostgreSQL embeddings to FAISS vector database",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--max', '-m',
        type=int,
        required=True,
        default=10000,
        help='Maximum number of papers to add (default: no limit, add all missing papers)'
    )
    
    parser.add_argument(
        '--batch-size', '-b',
        type=int,
        default=1000,
        help='Number of papers to fetch from database per query (default: 1000)'
    )
    
    args = parser.parse_args()
    
    asyncio.run(sync_db_to_faiss(max_papers_to_add=args.max, batch_size=args.batch_size))
