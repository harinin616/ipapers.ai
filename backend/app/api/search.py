from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import logging
import asyncio
from fastapi.concurrency import run_in_threadpool

from app.models.paper import PaperSearchRequest, PaperSearchResponse, Paper
from app.services.db_service import db_service
from app.services.vector_search_service import vector_search_service
from app.services.keyword_search_service import keyword_search_service 
from app.services.llm_service import llm_service
from app.services import search_log_service
from app.services.arxiv_search_service import arxivsearch_service
from app.services.search_summary_service import search_summary_service
logger = logging.getLogger(__name__)

router = APIRouter()

def fallback_order(papers, ordered_pairs, limit):
    """
    Deterministic ordering used when the LLM reranker is unavailable or returns nothing.
    Papers follow the retrieval order (keyword hits first, then vector hits); anything not in
    `ordered_pairs` goes last in its original order. Returns at most `limit` papers.
    """
    rank = {}
    for i, pair in enumerate(ordered_pairs):
        rank.setdefault((pair[0], pair[1]), i)
    big = len(rank) + len(papers)
    indexed = sorted(
        enumerate(papers),
        key=lambda ip: (rank.get((ip[1].paper_id, ip[1].platform), big), ip[0]),
    )
    ordered = [p for _, p in indexed]
    return ordered[:limit] if limit and limit > 0 else ordered


@router.post("/", response_model=PaperSearchResponse)
async def search_papers(search_request: PaperSearchRequest):
    """
    get results from local vector search
    then rerank the results by LLM
    """
    try:
        logger.info(f"Received search request: {search_request.query}")
        
        vec_task   = asyncio.create_task(vector_search_service.search(query=search_request.query))
        #arxiv_task = asyncio.create_task(arxivsearch_service.search(query=search_request.query))
        
        keyword_task= asyncio.create_task(keyword_search_service.search(query=search_request.query))


        vec_res, kw_res = await asyncio.gather(vec_task, keyword_task, return_exceptions=True)
        if isinstance(vec_res, Exception):
            logger.warning(f"Vector search failed, continuing with keyword results only: {vec_res}")
            vec_res = []
        if isinstance(kw_res, Exception):
            logger.warning(f"Keyword search failed, continuing with vector results only: {kw_res}")
            kw_res = []
        paper_id_platform_pairs, keyword_paper_id_platform_pairs = vec_res, kw_res
        #paper_id_platform_pairs = await vec_task
        #arxiv_papers, 
    

        # --- 将本地的召回结果ID进行高效融合 ---
        # 使用集合(set)的并集操作，可以自动合并和去重
        combined_local_ids = list(dict.fromkeys([*keyword_paper_id_platform_pairs, *paper_id_platform_pairs]))

        if not combined_local_ids:# and not arxiv_papers:
            return PaperSearchResponse(results=[], count=0)
        
        logger.info(f"Found {len(paper_id_platform_pairs)} paper IDs from vector search")
        logger.info(f"Found {len(keyword_paper_id_platform_pairs)} paper IDs from keyword search")
        logger.info(f"Total unique local IDs to fetch: {len(combined_local_ids)}")
        #logger.info(f"Found {len(arxiv_papers)} papers from arXiv search")

        papers = await db_service.get_papers_by_ids(combined_local_ids)

        # 去重
        unique = []
        seen_titles = set()

        for p in papers:
            if p.title not in seen_titles:
                unique.append(p)
                seen_titles.add(p.title)

    #    for p in arxiv_papers:
     #       if p.title not in seen_titles:
      #          unique.append(p)
       #         seen_titles.add(p.title)

        papers = unique
        

        documents=[p.title+p.abstract for p in papers]
        try:
            rerank = await llm_service.get_rerank(documents=documents, query=search_request.query)
        except Exception as e:
            logger.warning(f"Rerank raised {e.__class__.__name__}: {e}")
            rerank = []
        rerank = [i for i in (rerank or []) if isinstance(i, int) and 0 <= i < len(papers)]
        if rerank:
            new_papers = [papers[idx] for idx in rerank]
        else:
            # Reranker unavailable or empty: fall back to retrieval order so users still get results.
            logger.warning("Reranker returned no ordering; falling back to retrieval order")
            topn = getattr(llm_service, "rerank_topn", None)
            new_papers = fallback_order(papers, combined_local_ids, topn if isinstance(topn, int) and topn > 0 else 50)
        logger.info(f"Reranked papers: {[p.pdf_url for p in new_papers]}")
        paper_responses = [
            Paper(
                paper_id=p.paper_id,
                title=p.title,
                authors=p.authors,
                abstract=p.abstract,
                categories=p.categories,
                pdf_url=p.pdf_url.replace("http://", "https://"),
                published_date=p.published_date,
                updated_date=p.updated_date,
                platform=p.platform  # 直接使用返回的platform属性
            ) for p in new_papers
        ]
        
        # Always return papers immediately, no summary generation in main search
        await search_log_service.append_record(
            query=search_request.query,
            results=[r.model_dump() for r in paper_responses]
        )
        return PaperSearchResponse(
            results=paper_responses,
            count=len(paper_responses),
            summary=None  # Summary will be generated separately
        )
        
    except Exception as e:
        logger.error(f"Error searching papers: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error searching papers: {str(e)}"
        ) 