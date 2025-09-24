#!/usr/bin/env python3
"""
Process embeddings for grants and add to vector search index
Similar to process_embeddings.py for papers
"""
import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import get_async_db
from app.models.db_models import DBGrant
from app.services.grant_db_service import grant_db_service
from app.services.grant_vector_search_service import grant_vector_search_service
from app.models.grant import Grant
from sqlalchemy.future import select

async def process_grant_embeddings_batch(grant_ids: list = None, process_all: bool = False):
    """
    Process embeddings for grants and add to vector search index
    """
    print("Processing grant embeddings...")
    
    async for db in get_async_db():
        try:
            if process_all:
                # Process all grants without embeddings
                result = await db.execute(
                    select(DBGrant).where(DBGrant.embedding.is_(None))
                )
                grants = result.scalars().all()
                print(f"Found {len(grants)} grants without embeddings")
            elif grant_ids:
                # Process specific grant IDs
                result = await db.execute(
                    select(DBGrant).where(DBGrant.grant_id.in_(grant_ids))
                )
                grants = result.scalars().all()
                print(f"Found {len(grants)} grants with specified IDs")
            else:
                print("No grants to process")
                return
            
            if not grants:
                print("No grants found to process")
                return
            
            # Convert DBGrant to Grant objects
            grant_objects = []
            for db_grant in grants:
                grant = Grant(
                    grant_id=db_grant.grant_id,
                    title=db_grant.title,
                    agency=db_grant.agency,
                    synopsis=db_grant.synopsis,
                    detail_url=db_grant.detail_url,
                    posted_date=db_grant.posted_date,
                    updated_date=db_grant.updated_date,
                    close_date=db_grant.close_date,
                    status=db_grant.status
                )
                grant_objects.append(grant)
            
            print(f"Processing {len(grant_objects)} grants...")
            
            # Add to database with embeddings
            added_ids = await grant_db_service.add_grants(grant_objects)
            print(f"Added {len(added_ids)} grants to database with embeddings")
            
            # Add to vector search index
            if added_ids:
                await grant_vector_search_service.add_grants(grant_objects)
                print(f"Added {len(added_ids)} grants to vector search index")
            
            print(f"Total grants in vector index: {grant_vector_search_service.index.ntotal}")
            
            # Test search
            print("\nTesting vector search...")
            results = await grant_vector_search_service.vector_search("education research", k=3)
            print(f"Search results for 'education research': {results}")
            
        except Exception as e:
            print(f"Error processing grant embeddings: {e}")
        break

async def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Process grant embeddings")
    parser.add_argument("--grant-ids", nargs="+", help="Specific grant IDs to process")
    parser.add_argument("--process-all", action="store_true", help="Process all grants without embeddings")
    
    args = parser.parse_args()
    
    if not args.grant_ids and not args.process_all:
        print("Please specify --grant-ids or --process-all")
        return
    
    await process_grant_embeddings_batch(
        grant_ids=args.grant_ids,
        process_all=args.process_all
    )

if __name__ == "__main__":
    asyncio.run(main())
