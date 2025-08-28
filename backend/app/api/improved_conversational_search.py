from fastapi import APIRouter, HTTPException, Request
from typing import List, Optional
import logging
from pydantic import BaseModel
from app.services.improved_conversational_search_service import improved_conversational_search_service

logger = logging.getLogger(__name__)
router = APIRouter()

class ConversationMessage(BaseModel):
    role: str
    content: str
    timestamp: Optional[str] = None

class ImprovedConversationalSearchRequest(BaseModel):
    session_id: str
    query: str
    conversation_history: Optional[List[ConversationMessage]] = []

class ImprovedConversationalSearchResponse(BaseModel):
    action: str  # "chat", "clarification", "results", "error"
    message: str
    papers: Optional[List[dict]] = []
    count: Optional[int] = 0
    refined_query: Optional[str] = None
    suggestions: Optional[List[str]] = []

class PaperAnalysisRequest(BaseModel):
    paper_id: str
    platform: str = "arxiv"

class PaperAnalysisResponse(BaseModel):
    analysis: str
    success: bool
    error_message: Optional[str] = None

@router.post("/search", response_model=ImprovedConversationalSearchResponse)
async def improved_conversational_search(
    request: Request,
    body: ImprovedConversationalSearchRequest
):
    """
    Improved conversational search - focuses on intent recognition and context understanding
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
                "timestamp": msg.timestamp
            })

        # Call improved conversational search service
        result = await improved_conversational_search_service.process_conversation(
            user_id=str(user_id),
            session_id=body.session_id,
            query=body.query,
            conversation_history=conversation_history
        )

        return ImprovedConversationalSearchResponse(
            action=result["action"],
            message=result["message"],
            papers=result.get("papers", []),
            count=result.get("count", 0),
            refined_query=result.get("refined_query"),
            suggestions=result.get("suggestions", [])
        )

    except Exception as e:
        logger.error(f"Error in improved conversational search: {e}")
        return ImprovedConversationalSearchResponse(
            action="error",
            message="Sorry, encountered an error processing your request. Please try again.",
            papers=[],
            count=0,
            suggestions=["Please describe your needs again", "Try using more specific keywords"]
        )

@router.post("/analyze-paper", response_model=PaperAnalysisResponse)
async def analyze_paper(
    request: Request,
    body: PaperAnalysisRequest
):
    """
    Analyze a paper by extracting its full text and using LLM to provide insights
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

        # Call paper analysis service
        result = await improved_conversational_search_service.analyze_paper(
            user_id=str(user_id),
            paper_id=body.paper_id,
            platform=body.platform
        )

        return PaperAnalysisResponse(
            analysis=result["analysis"],
            success=result["success"],
            error_message=result.get("error_message")
        )

    except Exception as e:
        logger.error(f"Error in paper analysis: {e}")
        return PaperAnalysisResponse(
            analysis="",
            success=False,
            error_message=f"Error analyzing paper: {str(e)}"
        )
