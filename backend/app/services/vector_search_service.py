import os
import logging
import numpy as np
import faiss
import asyncio 
from typing import List, Optional, Tuple, Union
import pickle
from pathlib import Path
import json

from app.models.paper import Paper
from app.services.llm_service import llm_service 

logger = logging.getLogger(__name__)

class VectorSearchService:
    """using faiss to handle vector search (IVF + PQ quantized in-memory version)"""
    
    def __init__(self):
        """
        Initialize vector search service
        """
        self.embedding_dim = llm_service.default_embedding_dimensions
        self.index = None
        self.paper_ids: List[str] = []
        self.paper_platforms: List[str] = []
        
        self.project_root = Path(__file__).parent.parent.parent
        self.data_dir = self.project_root / "data"
        self.index_path = str(self.data_dir / "paper_index.faiss")
        self.paper_ids_path = str(self.data_dir / "paper_ids.pkl")
        self.paper_platforms_path = str(self.data_dir / "paper_platforms.pkl")

        # ==== IVF + PQ 配置 ====
        # 可以通过环境变量覆盖：
        #   FAISS_IVF_NLIST: 粗聚类个数
        #   FAISS_PQ_M: PQ 子向量个数
        #   FAISS_NPROBE: 搜索时探测的列表数
        self.ivf_nlist = int(os.getenv("FAISS_IVF_NLIST", "65536"))
        env_pq_m = os.getenv("FAISS_PQ_M")

        if env_pq_m is not None:
            self.pq_m = int(env_pq_m)
        else:
            # 如果用户没指定，就自动挑一个能整除 embedding_dim 的 m
            # 从大到小尝试几组常用值
            self.pq_m = None
            for candidate in [128, 64, 48, 32, 24, 16, 8, 4]:
                if self.embedding_dim % candidate == 0:
                    self.pq_m = candidate
                    break
            if self.pq_m is None:
                raise ValueError(
                    f"embedding_dim={self.embedding_dim} 不能被常用的 PQ m 值整除，"
                    f"请手动设置环境变量 FAISS_PQ_M 为 embedding_dim 的一个因子。"
                )

        self.nprobe = int(os.getenv("FAISS_NPROBE", "64"))
        self.index_key = f"IVF{self.ivf_nlist},PQ{self.pq_m}"

        logger.info(
            f"VectorSearchService initialized "
            f"(dim={self.embedding_dim}, index_key={self.index_key}, nprobe={self.nprobe})"
        )
        
        self.load_index()
    
    def load_index(self):
        """Load FAISS index and ID list from disk if they exist"""
        import gc
        gc.collect()
        
        try:
            if os.path.exists(self.index_path) and os.path.exists(self.paper_ids_path):
                # 对量化索引直接读到内存，不再 READ_ONLY
                self.index = faiss.read_index(self.index_path)
               
                # 设置 nprobe（如果是 IVF 索引）
                if hasattr(self.index, "nprobe"):
                    self.index.nprobe = self.nprobe

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
                    logger.warning(
                        f"Mismatch between paper_ids ({len(self.paper_ids)}) "
                        f"and platforms ({len(self.paper_platforms)}) count"
                    )
                    # Pad platforms list if shorter
                    if len(self.paper_platforms) < len(self.paper_ids):
                        self.paper_platforms.extend(
                            ["arxiv"] * (len(self.paper_ids) - len(self.paper_platforms))
                        )
                    # Truncate platforms list if longer
                    elif len(self.paper_platforms) > len(self.paper_ids):
                        self.paper_platforms = self.paper_platforms[:len(self.paper_ids)]
                
                if self.index.ntotal != len(self.paper_ids):
                    logger.warning(
                        f"Index vector count ({self.index.ntotal}) "
                        f"and ID count ({len(self.paper_ids)}) mismatch"
                    )
            else:
                self.create_new_index()
        except Exception as e:
            logger.error(f"Error loading index: {e}. Creating new index.")
            self.create_new_index()
            
    def create_new_index(self):
        """Create a new empty FAISS IVF+PQ index in memory"""
        # IVF + PQ，内积度量
        logger.info(
            f"Creating new FAISS IVF+PQ index with key='{self.index_key}', "
            f"dim={self.embedding_dim}"
        )
        self.index = faiss.index_factory(
            self.embedding_dim,
            self.index_key,
            faiss.METRIC_INNER_PRODUCT
        )

        # IVF 索引用 nprobe 控制查询时探测的 list 数
        if hasattr(self.index, "nprobe"):
            self.index.nprobe = self.nprobe

        self.paper_ids = []
        self.paper_platforms = []
        logger.info(f"Created new empty FAISS IVF+PQ index")

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
                
            logger.info(
                f"Saved FAISS index with {self.index.ntotal} vectors "
                f"and {len(self.paper_ids)} IDs."
            )
        except Exception as e:
            logger.error(f"Error saving index: {e}")
    
    async def embed_texts(self, texts: List[str]) -> Optional[List[np.ndarray]]:
        """
        Generate embeddings for a list of texts using llm_service.
        """
        if not texts:
             return []
             
        embeddings = await llm_service.get_embeddings(
            texts=texts,
        )
        
        # 归一化后用 inner product ≈ cosine
        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

        if embeddings is None:
             return None
             
        return [np.array(emb, dtype='float32') for emb in embeddings]

    async def add_papers(self, papers: List[Paper]):
        """
        add papers to the index
        """
        # 使用元组(paper_id, platform)作为去重键
        processed_paper_keys = set(
            (paper_id, platform)
            for paper_id, platform in zip(self.paper_ids, self.paper_platforms)
        )
        
        print(f"Index currently has {len(processed_paper_keys)} unique papers")

        texts_to_embed: List[str] = []
        new_paper_ids: List[str] = [] 
        new_paper_platforms: List[str] = []

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
                    logger.warning(
                        f"Paper {paper_id} (platform: {platform}) has no text to embed. Skipping."
                    )
                     
        if not texts_to_embed:
            logger.info("No new papers to add to the index")
            return

        total_texts_to_process = len(texts_to_embed)
        logger.info(f"Preparing to get embeddings for {total_texts_to_process} new papers")
        
        all_embeddings = await self.embed_texts(texts_to_embed)

        if not all_embeddings:
            logger.error("embedding requests failed")
            return

        embeddings_array = np.array(all_embeddings, dtype='float32')

        try:
            # IVF / PQ 索引需要先 train 再 add
            if hasattr(self.index, "is_trained") and not self.index.is_trained:
                # 用当前这批数据做训练（实际工程中可以采样/累积更多再训）
                train_x = embeddings_array
                max_train = 100_000
                if train_x.shape[0] > max_train:
                    # 随机采样一部分做训练
                    idx = np.random.choice(train_x.shape[0], max_train, replace=False)
                    train_x = train_x[idx]
                logger.info(
                    f"Training FAISS IVF+PQ index on {train_x.shape[0]} vectors "
                    f"(index_key={self.index_key})"
                )
                self.index.train(train_x)
                logger.info("FAISS index training finished")

            # 训练完成后再 add
            self.index.add(embeddings_array)
            self.paper_ids.extend(new_paper_ids)
            self.paper_platforms.extend(new_paper_platforms)
            self.save_index()
             
        except Exception as e:
            logger.error(f"Error adding vectors to index or saving: {e}", exc_info=True)
            raise
    
    async def vector_search(self, query: str, k: int = 50) -> List[Tuple[str, str]]:
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
            
            logger.info(
                f"Query embedding for '{query}' generated, "
                f"shape: {query_embedding_list[0].shape if query_embedding_list else 'None'}"
            )

            if not query_embedding_list or query_embedding_list[0] is None:
                logger.error(f"Failed to get embedding for query: '{query}'")
                return []
                 
            query_embedding = query_embedding_list[0].reshape(1, -1) 
                 
            scores, indices = self.index.search(query_embedding, k)
            
            # 返回(paper_id, platform)元组列表
            result_tuples: List[Tuple[str, str]] = []
            for idx in indices[0]:
                if 0 <= idx < len(self.paper_ids):
                    paper_id = self.paper_ids[idx]
                    platform = self.paper_platforms[idx]
                    result_tuples.append((paper_id, platform))
            
            logger.debug(f"Search query '{query}' found {len(result_tuples)} results.")
            logger.info(f"FAISS index currently holds {len(self.paper_ids)} papers.")

            return result_tuples
            
        except Exception as e:
            logger.error(f"Error searching index: {e}", exc_info=True)
            return []
            
    async def search(self, query: str, k: int = 80) -> List[Tuple[str, str]]:
            system_prompt = (
                "You are a professional information-retrieval assistant. Given a user query, "
                "generate a concise and semantically faithful reformulation for vector search. "
                "The output should be a single line containing a few meaningful keywords or "
                "short phrases, separated by commas.\n\n"
                "Requirements:\n\n"
                "Stay semantically close to the original query\n\n"
                "Avoid irrelevant or overly broad expansions\n\n"
                "Be concise: a few keywords or short noun phrases only\n\n"
                "Output only the result line, no explanation, no quotes, no numbering"
            )
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": query}
            ]
            try:
                response = await llm_service.get_conversation_completion(
                    messages=messages,
                    stream=False,
                    model=llm_service.query_model
                )
                reformulated = response.text.strip()
                if not reformulated:
                    logger.warning("LLM returned empty string; fallback to original query")
                    reformulated = query
            except Exception as e:
                logger.error(f"LLM call failed ({e}); fallback to original query")
                reformulated = query

            reformulated_results = await self.vector_search(reformulated, k=k)
            
            # 合并结果并去重
            seen = set()
            result_tuples: List[Tuple[str, str]] = []
            for result in reformulated_results:
                if result not in seen:
                    seen.add(result)
                    result_tuples.append(result)

            return result_tuples
                
vector_search_service = VectorSearchService()
