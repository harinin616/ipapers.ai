from fastapi import APIRouter, HTTPException
import logging
import asyncio

from app.models.paper import PaperSearchRequest, PaperSearchResponse, Paper
from app.services.db_service import db_service
from app.services.vector_search_service import vector_search_service
from app.services.llm_service import llm_service
from app.services.arxiv_search_service import arxivsearch_service
from app.services import search_log_service

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/", response_model=PaperSearchResponse)
async def search_papers(search_request: PaperSearchRequest):
    """
    get results from local vector search and arxiv search
    then rerank the results by LLM
    """
    try:
        logger.info(f"Received search request: {search_request.query}")

        vec_task   = asyncio.create_task(vector_search_service.search(query=search_request.query))
        arxiv_task = asyncio.create_task(arxivsearch_service.search(query=search_request.query))
        paper_ids, arxiv_papers = await asyncio.gather(vec_task, arxiv_task)
        
        if not paper_ids:
            return PaperSearchResponse(results=[], count=0)
        
        logger.info(f"Found {len(paper_ids)} paper IDs from vector search")
        logger.info(f"Found {len(arxiv_papers)} papers from arxiv search")

        papers = await db_service.get_papers_by_ids(paper_ids)

        existing_paper_ids = {p.paper_id for p in papers}
        
        for arxiv_paper in arxiv_papers:
            if arxiv_paper.paper_id not in existing_paper_ids:
                papers.append(arxiv_paper)
                existing_paper_ids.add(arxiv_paper.paper_id)


        unique = []
        seen_titles = set()

        for p in papers:
            if p.title not in seen_titles:
                unique.append(p)
                seen_titles.add(p.title)

        papers = unique

        documents=[p.title+p.abstract for p in papers]
        rerank = await llm_service.get_rerank(documents=documents,query=search_request.query)

        new_papers=[papers[idx] for idx in rerank]
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
                updated_date=p.updated_date
            ) for p in new_papers
        ]
        await search_log_service.append_record(
            query=search_request.query,
            results=[r.model_dump() for r in paper_responses]
        )
        return PaperSearchResponse(
            results=paper_responses,
            count=len(paper_responses)
        )
        
    except Exception as e:
        logger.error(f"Error searching papers: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error searching papers: {str(e)}"
        ) 