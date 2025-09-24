from fastapi import APIRouter, HTTPException, Request, Body
from typing import List, Optional
import logging
from pydantic import BaseModel
from app.services.improved_grant_search_service import improved_grant_search_service

logger = logging.getLogger(__name__)
router = APIRouter()

class GrantSearchMessage(BaseModel):
    role: str
    content: str
    timestamp: Optional[str] = None
    grants: Optional[List[dict]] = None

class ImprovedGrantSearchRequest(BaseModel):
    session_id: str
    query: str
    conversation_history: Optional[List[GrantSearchMessage]] = []

class ImprovedGrantSearchResponse(BaseModel):
    action: str  # "chat", "clarification", "results", "error"
    message: str
    grants: Optional[List[dict]] = []
    count: Optional[int] = 0
    refined_query: Optional[str] = None
    suggestions: Optional[List[str]] = []

@router.get("/debug/status")
async def debug_grant_status():
    """Debug endpoint to check grant data and vector index status"""
    try:
        from app.services.grant_vector_search_service import grant_vector_search_service
        from app.db.database import get_async_db
        from app.models.db_models import DBGrant
        from sqlalchemy.future import select
        
        # Check database
        async for db in get_async_db():
            result = await db.execute(select(DBGrant))
            all_grants = result.scalars().all()
            
            result = await db.execute(select(DBGrant).where(DBGrant.embedding.isnot(None)))
            grants_with_embeddings = result.scalars().all()
            
            return {
                "total_grants": len(all_grants),
                "grants_with_embeddings": len(grants_with_embeddings),
                "vector_index_size": grant_vector_search_service.index.ntotal,
                "vector_index_grant_ids": len(grant_vector_search_service.grant_ids),
                "sample_grant": {
                    "title": all_grants[0].title if all_grants else None,
                    "has_embedding": all_grants[0].embedding is not None if all_grants else None
                } if all_grants else None
            }
    except Exception as e:
        return {"error": str(e)}

@router.post("/process_embeddings")
async def process_grant_embeddings(
    request: Request,
    data: dict = Body(...)
):
    """
    Process embeddings for grants and add to vector search index
    Similar to paper process_embeddings
    """
    user_id = request.headers.get('X-User-ID')
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="User ID not found"
        )
    
    grant_ids = data.get("grant_ids", [])
    process_all = data.get("process_all", False)
    
    if not grant_ids and not process_all:
        raise HTTPException(
            status_code=400,
            detail="Missing grant_ids or process_all flag"
        )
    
    if user_id.isdigit():
        user_id = await db_service.get_uuid_by_user_id(int(user_id))
    
    try:
        from app.services.grant_vector_search_service import grant_vector_search_service
        from app.db.database import get_async_db
        from app.models.db_models import DBGrant
        from sqlalchemy.future import select
        from app.models.grant import Grant
        
        processed_count = 0
        
        async for db in get_async_db():
            if process_all:
                # Process all grants without embeddings
                result = await db.execute(
                    select(DBGrant).where(DBGrant.embedding.is_(None))
                )
                grants = result.scalars().all()
            else:
                # Process specific grant IDs
                result = await db.execute(
                    select(DBGrant).where(DBGrant.grant_id.in_(grant_ids))
                )
                grants = result.scalars().all()
            
            if not grants:
                return {"message": "No grants found to process", "processed_count": 0}
            
            # Convert DBGrant to Grant objects
            grant_objects = []
            for db_grant in grants:
                grant = Grant(
                    grant_id=db_grant.grant_id,
                    title=db_grant.title,
                    agency=db_grant.agency,
                    synopsis=db_grant.synopsis,
                    detail_url=db_grant.detail_url,
                    posted_date=db_grant.posted_date,
                    updated_date=db_grant.updated_date,
                    close_date=db_grant.close_date,
                    status=db_grant.status
                )
                grant_objects.append(grant)
            
            # Add to database with embeddings
            added_ids = await grant_db_service.add_grants(grant_objects)
            processed_count += len(added_ids)
            
            # Add to vector search index
            if added_ids:
                await grant_vector_search_service.add_grants(grant_objects)
            
            break
        
        return {
            "message": f"Successfully processed {processed_count} grants",
            "processed_count": processed_count,
            "vector_index_size": grant_vector_search_service.index.ntotal
        }
    
    except Exception as e:
        logger.error(f"Error processing grant embeddings for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing embeddings: {str(e)}")

@router.post("/search", response_model=ImprovedGrantSearchResponse)
async def improved_grant_search(
    request: Request,
    body: ImprovedGrantSearchRequest
):
    """
    Improved grant search - focuses on grant-specific search and analysis
    """
    try:
        user_id = request.headers.get('X-User-ID')
        if not user_id:
            raise HTTPException(
                status_code=401,
                detail="User ID not found"
            )
        
        if user_id.isdigit():
            from app.services.db_service import db_service
            user_id = await db_service.get_uuid_by_user_id(int(user_id))

        # Convert conversation history format
        conversation_history = []
        for msg in body.conversation_history:
            conversation_history.append({
                "role": msg.role,
                "content": msg.content,
                "timestamp": msg.timestamp,
                "grants": msg.grants
            })

        # Call improved grant search service
        result = await improved_grant_search_service.process_grant_search(
            user_id=str(user_id),
            session_id=body.session_id,
            query=body.query,
            conversation_history=conversation_history
        )
        
        return ImprovedGrantSearchResponse(
            action=result["action"],
            message=result["message"],
            grants=result.get("grants", []),
            count=result.get("count", 0),
            refined_query=result.get("refined_query"),
            suggestions=result.get("suggestions", [])
        )

    except Exception as e:
        logger.error(f"Error in improved grant search: {e}")
        return ImprovedGrantSearchResponse(
            action="error",
            message="Sorry, encountered an error processing your grant search request. Please try again.",
            grants=[],
            count=0,
            suggestions=["Please describe your grant search needs again", "Try using more specific keywords"]
        )
