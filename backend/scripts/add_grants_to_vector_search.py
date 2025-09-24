#!/usr/bin/env python3
"""
Add grants from database to vector search index
Similar to how papers are added to vector search
"""
import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import get_async_db
from app.models.db_models import DBGrant
from app.services.grant_vector_search_service import grant_vector_search_service
from sqlalchemy.future import select

async def add_grants_to_vector_search():
    """Add grants from database to vector search index"""
    print("Adding grants from database to vector search index...")
    
    async for db in get_async_db():
        try:
            # Get all grants with embeddings
            result = await db.execute(
                select(DBGrant).where(DBGrant.embedding.isnot(None))
            )
            grants = result.scalars().all()
            
            if not grants:
                print("No grants with embeddings found in database")
                return
            
            print(f"Found {len(grants)} grants with embeddings in database")
            
            # Convert DBGrant objects to Grant objects for vector search
            from app.models.grant import Grant
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
            
            # Add to vector search index
            await grant_vector_search_service.add_grants(grant_objects)
            
            print(f"Successfully added {len(grant_objects)} grants to vector search index")
            print(f"Total grants in vector index: {grant_vector_search_service.index.ntotal}")
            
            # Test search
            print("\nTesting vector search...")
            results = await grant_vector_search_service.vector_search("education research", k=3)
            print(f"Search results for 'education research': {results}")
            
        except Exception as e:
            print(f"Error adding grants to vector search: {e}")
        break

if __name__ == "__main__":
    asyncio.run(add_grants_to_vector_search())
