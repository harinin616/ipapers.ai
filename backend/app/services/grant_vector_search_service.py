import logging
import numpy as np
import faiss
import os
import pickle
from typing import List, Optional, Tuple
from pathlib import Path
from app.services.llm_service import llm_service

logger = logging.getLogger(__name__)

class GrantVectorSearchService:
    """Vector search service for grants using FAISS"""

    def __init__(self):
        self.index = None
        self.grant_ids = []
        self.dimension = 768  # Same as papers
        
        # Set up paths
        self.project_root = Path(__file__).parent.parent.parent
        self.data_dir = self.project_root / "data"
        self.index_path = str(self.data_dir / "grant_index.faiss")
        self.grant_ids_path = str(self.data_dir / "grant_ids.pkl")
        
        logger.info("GrantVectorSearchService initialized")
        self._load_index()

    def _load_index(self):
        """Load existing index or create new one"""
        try:
            if os.path.exists(self.index_path) and os.path.exists(self.grant_ids_path):
                self.index = faiss.read_index(self.index_path)
                with open(self.grant_ids_path, 'rb') as f:
                    self.grant_ids = pickle.load(f)
                logger.info(f"Loaded grant vector index with {len(self.grant_ids)} grants")
            else:
                self.index = faiss.IndexFlatIP(self.dimension)  # Inner product for cosine similarity
                self.grant_ids = []
                logger.info("Created new grant vector index")
                # Try to load grants from database and build index
                self._build_index_from_db()
        except Exception as e:
            logger.error(f"Error loading grant vector index: {e}")
            self.index = faiss.IndexFlatIP(self.dimension)
            self.grant_ids = []
            # Try to build index from database
            self._build_index_from_db()

    def _build_index_from_db(self):
        """Build index from grants in database"""
        try:
            import asyncio
            # Create a new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._async_build_index_from_db())
            loop.close()
        except Exception as e:
            logger.error(f"Error building index from database: {e}")

    async def _async_build_index_from_db(self):
        """Async helper to build index from database"""
        try:
            from app.db.database import get_async_db
            from app.models.db_models import DBGrant
            from sqlalchemy.future import select
            
            async for db in get_async_db():
                # Get all grants with embeddings
                result = await db.execute(
                    select(DBGrant).where(DBGrant.embedding.isnot(None))
                )
                grants = result.scalars().all()
                
                if not grants:
                    logger.info("No grants with embeddings found in database")
                    return
                
                logger.info(f"Found {len(grants)} grants with embeddings in database")
                
                # Extract embeddings and grant IDs
                embeddings = []
                grant_ids = []
                
                for grant in grants:
                    if grant.embedding:
                        embeddings.append(grant.embedding)
                        grant_ids.append(grant.grant_id)
                
                if embeddings:
                    # Convert to numpy array
                    embeddings_array = np.array(embeddings).astype('float32')
                    
                    # Add to index
                    self.index.add(embeddings_array)
                    self.grant_ids = grant_ids
                    
                    # Save index
                    self._save_index()
                    
                    logger.info(f"Built grant vector index with {len(grant_ids)} grants from database")
                break
                
        except Exception as e:
            logger.error(f"Error building index from database: {e}")


    def _save_index(self):
        """Save index to disk"""
        try:
            os.makedirs(self.data_dir, exist_ok=True)
            faiss.write_index(self.index, self.index_path)
            with open(self.grant_ids_path, 'wb') as f:
                pickle.dump(self.grant_ids, f)
            logger.info(f"Saved grant vector index with {len(self.grant_ids)} grants")
        except Exception as e:
            logger.error(f"Error saving grant vector index: {e}")

    async def embed_texts(self, texts: List[str]) -> Optional[List[np.ndarray]]:
        """Get embeddings for texts"""
        try:
            embeddings = await llm_service.get_embeddings(texts)
            if embeddings is None:
                return None
            return [np.array(emb, dtype='float32') for emb in embeddings]
        except Exception as e:
            logger.error(f"Error getting embeddings: {e}")
            return None

    async def add_grants(self, grants: List):
        """Add grants to the vector index"""
        try:
            # Filter out grants already in index
            existing_ids = set(self.grant_ids)
            new_grants = [g for g in grants if g.grant_id not in existing_ids]
            
            if not new_grants:
                logger.info("No new grants to add to index")
                return

            # Prepare texts for embedding
            texts_to_embed = []
            new_grant_ids = []
            
            for grant in new_grants:
                text = f"{grant.title} {grant.synopsis or ''}".strip()
                if text:
                    texts_to_embed.append(text)
                    new_grant_ids.append(grant.grant_id)
                else:
                    logger.warning(f"Grant {grant.grant_id} has no text to embed")

            if not texts_to_embed:
                logger.info("No texts to embed for new grants")
                return

            # Get embeddings
            embeddings = await self.embed_texts(texts_to_embed)
            if not embeddings:
                logger.error("Failed to get embeddings for grants")
                return

            # Add to index
            embeddings_array = np.array(embeddings).astype('float32')
            self.index.add(embeddings_array)
            self.grant_ids.extend(new_grant_ids)
            self._save_index()
            
            logger.info(f"Added {len(new_grant_ids)} grants to vector index")

        except Exception as e:
            logger.error(f"Error adding grants to vector index: {e}")

    async def vector_search(self, query: str, k: int = 50) -> List[Tuple[str, float]]:
        """Search for similar grants"""
        try:
            if self.index.ntotal == 0:
                return []

            # Get query embedding
            query_embeddings = await self.embed_texts([query])
            if not query_embeddings:
                return []

            query_vector = np.array(query_embeddings[0]).reshape(1, -1).astype('float32')
            
            # Search
            scores, indices = self.index.search(query_vector, min(k, self.index.ntotal))
            
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx < len(self.grant_ids):
                    results.append((self.grant_ids[idx], float(score)))
            
            return results

        except Exception as e:
            logger.error(f"Error in vector search: {e}")
            return []



grant_vector_search_service = GrantVectorSearchService()
