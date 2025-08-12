from fastapi import APIRouter, HTTPException, Query, Request
from typing import List, Optional
import logging

from app.models.paper import Paper
from app.services.recommendation_service import recommendation_service

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/user", response_model=List[Paper])
async def get_user_recommendations(
    request: Request,
    limit: int = Query(20, ge=1, le=50, description="Maximum number of recommendations"),
    exclude_existing: bool = Query(True, description="Exclude papers already in user's folders")
):
    """
    Get paper recommendations based on user's existing papers in all folders
    
    Query parameters:
    - limit: Maximum number of recommendations to return (1-50)
    - exclude_existing: Whether to exclude papers already in user's folders
    """
    try:
        # Get user ID from request headers
        user_id = request.headers.get("X-User-ID")
        if not user_id:
            raise HTTPException(status_code=401, detail="X-User-ID header missing")
        
        logger.info(f"Getting recommendations for user {user_id}")
        
        # Generate recommendations
        recommendations = await recommendation_service.get_user_paper_recommendations(
            user_id=user_id,
            limit=limit,
            exclude_existing=exclude_existing
        )
        
        logger.info(f"Returning {len(recommendations)} recommendations for user {user_id}")
        return recommendations
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user recommendations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/folder/{folder_id}", response_model=List[Paper])
async def get_folder_recommendations(
    folder_id: int,
    limit: int = Query(20, ge=1, le=50, description="Maximum number of recommendations"),
    exclude_existing: bool = Query(True, description="Exclude papers already in the folder")
):
    """
    Get paper recommendations based on papers in a specific folder
    
    Path parameters:
    - folder_id: ID of the folder to base recommendations on
    
    Query parameters:
    - limit: Maximum number of recommendations to return (1-50)
    - exclude_existing: Whether to exclude papers already in the folder
    """
    try:
        logger.info(f"Getting recommendations for folder {folder_id}")
        
        # Generate recommendations
        recommendations = await recommendation_service.get_folder_based_recommendations(
            folder_id=folder_id,
            limit=limit,
            exclude_existing=exclude_existing
        )
        
        logger.info(f"Returning {len(recommendations)} recommendations for folder {folder_id}")
        return recommendations
        
    except Exception as e:
        logger.error(f"Error getting folder recommendations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/health")
async def recommendations_health():
    """
    Health check endpoint for recommendations service
    """
    return {"status": "healthy", "service": "recommendations"}
