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
    keyword: str = Query(None),
    offset: int = Query(0, ge=0)
):
    """
    Get recent papers from database
    """
    if keyword:
        papers_1 = await db_service.get_recent_papers(limit=10, keyword=keyword, offset=offset)
        paper_tuples_2 = await vector_search_service.vector_search(keyword, 10)
    else:
        #print("No keyword")
        papers_1 = await db_service.get_recent_papers(limit=30, keyword=keyword, offset=offset)
        paper_tuples_2 = None
    
    # Convert paper_tuples to Paper objects
    papers_2 = []
    if paper_tuples_2:
        # paper_tuples_2 contains (paper_id, platform) tuples
        papers_2 = await db_service.get_papers_by_ids(paper_tuples_2)
    
    papers = papers_1 + papers_2
    
    # Manual deduplication using paper_id and platform
    seen_keys = set()
    unique_papers = []
    for paper in papers:
        key = (paper.paper_id, paper.platform)
        if key not in seen_keys:
            seen_keys.add(key)
            unique_papers.append(paper)
    
    papers = unique_papers
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