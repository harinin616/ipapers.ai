import os
import logging
import numpy as np
import faiss
import asyncio 
from typing import List, Optional, Tuple, Union
import pickle
from pathlib import Path
import json
from app.services.llm_service import llm_service 
from app.models.paper import Paper
from app.services.conv_llm_service import conv_llm_service 

logger = logging.getLogger(__name__)

class ConvVectorSearchService:
    """using faiss to handle vector search"""
    
    def __init__(self):
        """
        Initialize vector search service
        """
        self.embedding_dim = conv_llm_service.default_embedding_dimensions
        self.index = None
        self.paper_ids = []
        self.paper_platforms = []
        
        self.project_root = Path(__file__).parent.parent.parent
        self.data_dir = self.project_root / "data"
        self.index_path = str(self.data_dir / "paper_index.faiss")
        self.paper_ids_path = str(self.data_dir / "paper_ids.pkl")
        self.paper_platforms_path = str(self.data_dir / "paper_platforms.pkl")
        
        logger.info(f"ConvVectorSearchService initialized")
        
        self.load_index()
    
    def load_index(self):
        """Load FAISS index and ID list from disk if they exist"""
        try:
            if os.path.exists(self.index_path) and os.path.exists(self.paper_ids_path):
                self.index = faiss.read_index(self.index_path)
               
                # Load paper_ids
                with open(self.paper_ids_path, 'rb') as f:
                    self.paper_ids = pickle.load(f)
                
                # Load paper_platforms
                if os.path.exists(self.paper_platforms_path):
                    with open(self.paper_platforms_path, 'rb') as f:
                        self.paper_platforms = pickle.load(f)
                else:
                    # If platforms file doesn't exist, fill with "arxiv" as default
                    self.paper_platforms = ["arxiv"] * len(self.paper_ids)
                
                # Ensure both lists have the same length
                if len(self.paper_ids) != len(self.paper_platforms):
                    logger.warning(f"Mismatch between paper_ids ({len(self.paper_ids)}) and platforms ({len(self.paper_platforms)}) count")
                    # Pad platforms list if shorter
                    if len(self.paper_platforms) < len(self.paper_ids):
                        self.paper_platforms.extend(["arxiv"] * (len(self.paper_ids) - len(self.paper_platforms)))
                    # Truncate platforms list if longer
                    elif len(self.paper_platforms) > len(self.paper_ids):
                        self.paper_platforms = self.paper_platforms[:len(self.paper_ids)]
                
                logger.info(f"Loaded FAISS index with {self.index.ntotal} vectors and {len(self.paper_ids)} IDs.")
                if self.index.ntotal != len(self.paper_ids):
                    logger.warning("Index vector count and ID count mismatch")
            else:
                self.create_new_index()
        except Exception as e:
            logger.error(f"Error loading index: {e}. Creating new index.")
            self.create_new_index()
            
    def create_new_index(self):
        """Create a new empty FAISS index"""
        self.index = faiss.IndexFlatIP(self.embedding_dim)
        self.paper_ids = []
        self.paper_platforms = []
        logger.info(f"Created new empty FAISS index")

    def save_index(self):
        """Save FAISS index and ID list to disk"""
        try:
            if self.index is None:
                 logger.error("Cannot save empty index")
                 return
            os.makedirs(self.data_dir, exist_ok=True)
            faiss.write_index(self.index, self.index_path)
            
            # Save paper_ids separately
            with open(self.paper_ids_path, 'wb') as f:
                pickle.dump(self.paper_ids, f)
                
            # Save paper_platforms separately
            with open(self.paper_platforms_path, 'wb') as f:
                pickle.dump(self.paper_platforms, f)
                
            logger.info(f"Saved FAISS index with {self.index.ntotal} vectors and {len(self.paper_ids)} IDs.")
        except Exception as e:
            logger.error(f"Error saving index: {e}")
    
    async def embed_texts(self, texts: List[str]) -> Optional[List[np.ndarray]]:
        """
        Generate embeddings for a list of texts using llm_service.
        """
        if not texts:
             return []
             
        embeddings = await conv_llm_service.get_embeddings(
            texts=texts,
        )
        
        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

        if embeddings is None:
             return None
             
        return [np.array(emb, dtype='float32') for emb in embeddings]

    async def add_papers(self, papers: List[Paper]):
        """
        add papers to the index
        """
        # 使用元组(paper_id, platform)作为去重键
        processed_paper_keys = set((paper_id, platform) for paper_id, platform in zip(self.paper_ids, self.paper_platforms))
        
        texts_to_embed = []
        new_paper_ids = [] 
        new_paper_platforms = []

        # filter out papers already in index and prepare texts
        for paper in papers:
            paper_id = paper.paper_id
            # 确保获取platform属性，如果不存在则默认为"arxiv"
            platform = getattr(paper, 'platform', 'arxiv')
            
            if (paper_id, platform) not in processed_paper_keys:
                text = f"{paper.title} {paper.abstract or ''}".strip()
                if text: 
                     texts_to_embed.append(text)
                     new_paper_ids.append(paper_id)
                     new_paper_platforms.append(platform)
                else:
                     logger.warning(f"Paper {paper_id} (platform: {platform}) has no text to embed. Skipping.")
                     
        if not texts_to_embed:
            logger.info("No new papers to add to the index")
            return

        total_texts_to_process = len(texts_to_embed)
        logger.info(f"Preparing to get embeddings for {total_texts_to_process} new papers")
        
        all_embeddings = await self.embed_texts(texts_to_embed)

        if not all_embeddings:
            logger.error("embedding requests failed")
            return

        embeddings_array = np.array(all_embeddings).astype('float32')


        try:
            self.index.add(embeddings_array)
            self.paper_ids.extend(new_paper_ids)
            self.paper_platforms.extend(new_paper_platforms)
            self.save_index()
             
        except Exception as e:
            logger.error(f"Error adding vectors to index or saving: {e}")
            raise
    
    async def vector_search(self, query: str, k: int = 50, allow_ids: Optional[set[Tuple[str, str]]] = None) -> List[Tuple[str, str]]:
        """
        vector search by a certain query
        
        Returns:
            List of tuples (paper_id, platform)
        """
        try:
            logger.info(f"Starting vector search for query: '{query}' with k={k}")
            
            if self.index is None or self.index.ntotal == 0:
                logger.warning("empty index!!!")
                return []
            
            # get query embedding
            query_embedding_list = await self.embed_texts([query])
            
            logger.info(f"Query embedding for '{query}' generated, shape: {query_embedding_list[0].shape if query_embedding_list else 'None'}")

            if not query_embedding_list or query_embedding_list[0] is None:
                 logger.error(f"Failed to get embedding for query: '{query}'")
                 return []
                 
            query_embedding = query_embedding_list[0].reshape(1, -1) 
            # If an allowlist is provided, restrict computation to only those IDs
            if allow_ids:
                logger.info(f"Vector search: allow_ids provided with {len(allow_ids)} entries")
                logger.info(f"Vector search: sample allow_ids: {list(allow_ids)[:3]}")
                # Map allowed (paper_id, platform) to index positions
                allowed_positions: List[int] = []
                tuple_to_pos = {}
                for pos, (pid, plat) in enumerate(zip(self.paper_ids, self.paper_platforms)):
                    tuple_to_pos[(pid, plat)] = pos
                
                matched_count = 0
                for tup in allow_ids:
                    pos = tuple_to_pos.get(tup)
                    if pos is not None:
                        allowed_positions.append(pos)
                        matched_count += 1
                
                logger.info(f"Vector search: {matched_count}/{len(allow_ids)} allow_ids matched in index")

                if not allowed_positions:
                    logger.warning("Allowlist provided but none matched index; returning empty result")
                    return []

                # Reconstruct vectors for allowed positions and compute scores manually
                try:
                    allowed_vecs = []
                    for pos in allowed_positions:
                        try:
                            vec = self.index.reconstruct(pos)
                            allowed_vecs.append(vec)
                        except Exception:
                            continue
                    if not allowed_vecs:
                        return []
                    vecs = np.stack(allowed_vecs).astype('float32')
                    # Normalize reconstructed vectors in case they are not unit-length
                    vecs = vecs / np.linalg.norm(vecs, axis=1, keepdims=True)
                    # Dot product with query embedding
                    scores = vecs @ query_embedding.squeeze(0)
                    topk = min(k, scores.shape[0])
                    top_indices = np.argpartition(-scores, topk - 1)[:topk]
                    # Sort topk by score desc
                    top_indices = top_indices[np.argsort(-scores[top_indices])]

                    result_tuples = []
                    for idx_local in top_indices:
                        pos = allowed_positions[idx_local]
                        paper_id = self.paper_ids[pos]
                        platform = self.paper_platforms[pos]
                        result_tuples.append((paper_id, platform))
                    
                    # Debug: Print vector search results
                    logger.info(f"=== VECTOR SEARCH DEBUG ===")
                    logger.info(f"Vector search returned {len(result_tuples)} results")
                    logger.info(f"Sample vector search results: {result_tuples[:5]}")
                    logger.info(f"=== END VECTOR SEARCH DEBUG ===")
                    
                    return result_tuples
                except Exception as e:
                    logger.error(f"Restricted vector search failed, falling back to full search: {e}")
                    # Fall through to full-index search and filter

            # Default: full-index search
            scores, indices = self.index.search(query_embedding, k)

            result_tuples = []
            for idx in indices[0]:
                if idx >= 0 and idx < len(self.paper_ids):
                    paper_id = self.paper_ids[idx]
                    platform = self.paper_platforms[idx]
                    result_tuples.append((paper_id, platform))
                   
            # Debug: Print vector search results (full search)
            logger.info(f"=== VECTOR SEARCH DEBUG (FULL) ===")
            logger.info(f"Vector search returned {len(result_tuples)} results")
            logger.info(f"Sample vector search results: {result_tuples[:5]}")
            logger.info(f"=== END VECTOR SEARCH DEBUG (FULL) ===")
            
            logger.debug(f"Search query'{query}' found {len(result_tuples)} results.")
            return result_tuples
            
        except Exception as e:
            logger.error(f"Error searching index: {e}", exc_info=True)
            return []
            
    async def search(self, query: str, k: int = 500, allow_ids: Optional[set[Tuple[str, str]]] = None) -> List[Tuple[str, str]]:


            reformulated = query

            logger.info(f"Reformulated query: {reformulated}")
            reformulated_results = await self.vector_search(reformulated, k=k, allow_ids=allow_ids)
            
            # 合并结果并去重
            seen = set()
            result_tuples = []
            for result in reformulated_results:#original_results + 
                if result not in seen:
                    seen.add(result)
                    result_tuples.append(result)

            return result_tuples
                
conv_vector_search_service = ConvVectorSearchService() 