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
            platform = getattr(paper, 'platform')
            
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


    async def vector_search(
        self, query: str, k: int = 50, allow_ids: Optional[set[Tuple[str, str]]] = None
    ) -> List[Tuple[str, str]]:
        """
        Vector search by query.
        Returns: List of tuples (paper_id, platform)
        """
        try:
            logger.info(f"Starting vector search for query: '{query}' with k={k}")

            if self.index is None or self.index.ntotal == 0:
                logger.warning("Empty index!")
                return []

            # Step 1: Get query embedding
            query_embedding_list = await self.embed_texts([query])
            if not query_embedding_list or query_embedding_list[0] is None:
                logger.error(f"Failed to get embedding for query: '{query}'")
                return []

            query_embedding = query_embedding_list[0].reshape(1, -1).astype("float32")
            logger.info(f"Query embedding ready, shape={query_embedding.shape}")

            # Step 2: If allowlist provided, restrict to those IDs
            if allow_ids:
                logger.info(f"Vector search: allow_ids provided with {len(allow_ids)} entries")

                # Map (paper_id, platform) -> FAISS index positions
                tuple_to_pos = {
                    (pid, plat): i for i, (pid, plat) in enumerate(zip(self.paper_ids, self.paper_platforms))
                }
                allowed_positions = [tuple_to_pos[tup] for tup in allow_ids if tup in tuple_to_pos]

                if not allowed_positions:
                    logger.warning("Allowlist provided but none matched index; returning empty result")
                    return []

                logger.info(f"{len(allowed_positions)} / {len(allow_ids)} allow_ids matched FAISS index")

                allowed_positions_np = np.array(allowed_positions, dtype="int64")

                # Try native FAISS filtering (if IVF type) but willnot work currently because we use IndexFlatIP
                try:
                    if "IVF" in type(self.index).__name__:
                        sel = faiss.IDSelectorBatch(allowed_positions_np)
                        params = faiss.SearchParametersIVF(sel=sel, nprobe=self.index.nprobe)
                        scores, indices = self.index.search(query_embedding, k, params=params)
                        logger.info(f"Vector search (filtered) returned {len(indices[0])} results")
                    else:
                        raise AttributeError("Index type does not support IDSelectorBatch")

                except Exception as e:
                    logger.warning(f"IDSelector filtering failed ({e}); using fallback search")

                    allowed_vecs = np.stack(
                        [self.index.reconstruct(pos) for pos in allowed_positions]
                    ).astype("float32")
                    allowed_vecs /= np.linalg.norm(allowed_vecs, axis=1, keepdims=True)

                    temp_index = faiss.IndexFlatIP(self.index.d)
                    temp_index.add(allowed_vecs)

                    scores, local_indices = temp_index.search(query_embedding, k)
                    indices = np.array([[allowed_positions[i] for i in local_indices[0]]])

                # Collect filtered results and return immediately ✅
                result_tuples = [
                    (self.paper_ids[idx], self.paper_platforms[idx])
                    for idx in indices[0]
                    if 0 <= idx < len(self.paper_ids)
                ]

                logger.info(f"=== VECTOR SEARCH DEBUG (ALLOWLIST) ===")
                logger.info(f"Scores sample: {scores[0][:5]}")
                logger.info(f"Sample results: {result_tuples[:5]}")
                logger.info(f"=== END VECTOR SEARCH DEBUG (ALLOWLIST) ===")

                return result_tuples  # ✅ ensure function exits here

            # Step 3: Default (full) FAISS search
            scores, indices = self.index.search(query_embedding, k)
            result_tuples = [
                (self.paper_ids[idx], self.paper_platforms[idx])
                for idx in indices[0]
                if 0 <= idx < len(self.paper_ids)
            ]

            logger.info(f"=== VECTOR SEARCH DEBUG (FULL) ===")
            logger.info(f"Vector search returned {len(result_tuples)} results")
            logger.info(f"Sample vector search results: {result_tuples[:5]}")
            logger.info(f"=== END VECTOR SEARCH DEBUG (FULL) ===")

            return result_tuples

        except Exception as e:
            logger.error(f"Error searching index: {e}", exc_info=True)
            return []
        
    async def search(self, query: str, k: int = 50, allow_ids: Optional[set[Tuple[str, str]]] = None) -> List[Tuple[str, str]]:


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