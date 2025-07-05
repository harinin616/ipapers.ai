from fastapi import APIRouter, HTTPException, Query
from typing import List
import logging

from app.models.paper import Paper
from app.services.db_service import db_service
from app.services.vector_search_service import vector_search_service

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/", response_model=List[Paper])
async def get_papers(
    limit: int = Query(30, ge=1, le=100),
    keyword: str = Query(None)
):
    """
    Get recent papers from database
    """
    papers_1 = await db_service.get_recent_papers(limit=10, keyword=keyword)
    papers_2 = await vector_search_service.vector_search(keyword, 10)
    papers = papers_1 + papers_2
    papers = list(set(papers))
    papers.sort(key=lambda x: x.published_date, reverse=True)
    return papers


@router.get("/count")
async def count_papers():
    """
    Get the total number of papers in the database
    """
    count = await db_service.count_papers()
    return count


@router.post("/click/{paper_id}")
async def click_paper(paper_id: str):
    """
    Click on a paper
    """
    success = await db_service.click_paper(paper_id)
    if not success:
        raise HTTPException(status_code=404, detail="Paper not found")
    return success

@router.get("/{paper_id}", response_model=Paper)
async def get_paper(paper_id: str):
    """
    Get paper by paper_id
    """
    paper = await db_service.get_paper_by_id(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
        
    response = Paper(
        paper_id=paper.paper_id,
        title=paper.title,
        authors=paper.authors,
        abstract=paper.abstract,
        categories=paper.categories,
        pdf_url=paper.pdf_url.replace("http://", "https://"),
        published_date=paper.published_date,
        updated_date=paper.updated_date
    )
    
    return response 