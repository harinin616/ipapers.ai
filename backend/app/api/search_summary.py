from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
import logging

from app.models.paper import Paper
from app.services.search_summary_service import search_summary_service

logger = logging.getLogger(__name__)

router = APIRouter()

class SearchSummaryRequest(BaseModel):
    """Model for search summary request"""
    query: str
    papers: List[Paper]
    summary_type: str = "full"  # "full" or "quick"

class SearchSummaryResponse(BaseModel):
    """Model for search summary response"""
    query: str
    summary: str
    paper_count: int

@router.post("/", response_model=SearchSummaryResponse)
async def generate_search_summary(request: SearchSummaryRequest):
    """
    Generate a summary for search results using the same approach as DailyFeed.
    
    Args:
        request: SearchSummaryRequest containing query, papers, and summary type
        
    Returns:
        SearchSummaryResponse with generated summary
    """
    try:
        logger.info(f"Generating {request.summary_type} summary for query: '{request.query}' with {len(request.papers)} papers")
        
        if not request.query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
        
        if not request.papers:
            raise HTTPException(status_code=400, detail="Papers list cannot be empty")
        
        # Generate summary based on type
        if request.summary_type == "quick":
            summary = search_summary_service.generate_quick_summary(
                query=request.query,
                papers=request.papers
            )
        else:
            summary = search_summary_service.generate_search_summary(
                query=request.query,
                papers=request.papers
            )
        
        return SearchSummaryResponse(
            query=request.query,
            summary=summary,
            paper_count=len(request.papers)
        )
        
    except Exception as e:
        logger.error(f"Error generating search summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error generating search summary: {str(e)}"
        )
