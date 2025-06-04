from fastapi import APIRouter, HTTPException, Body, Path, Request, Query
from fastapi.responses import StreamingResponse
from typing import Optional
import logging
import json

from app.services.review_service import review_service

logger = logging.getLogger(__name__)

router = APIRouter()


class ReviewResponseChunk:
    """
    Stream response chunk for review
    """
    def __init__(self, content: str, done: bool = False):
        self.content = content
        self.done = done
    
    def to_json(self) -> str:
        """
        change response chunk to json string
        """
        return json.dumps({
            "content": self.content,
            "done": self.done
        }, ensure_ascii=False)


@router.post("/chat_comparison")
async def chat_comparison(
    request: Request,
    message: str = Body(embed=True)
):
    """
    get stream response for paper comparison
    """
    user_id = request.headers.get('X-User-ID')
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="User ID not found"
        )

    if user_id not in review_service.active_reviews:
        review_service.active_reviews[user_id] = {
            "comparison_messages": [],
            "rwg_messages": [],
            "files": []
        }
    
    async def stream_comparison_response():
        try:
            async for content_chunk, is_done in review_service.generate_comparison_response(user_id, message):
                response_chunk = ReviewResponseChunk(content=content_chunk, done=is_done)
                json_chunk = response_chunk.to_json() + "\n"
                yield json_chunk
        except Exception as e:
            logger.error(f"Error in stream_comparison_response: {str(e)}")
            error_chunk = ReviewResponseChunk(content="Error processing comparison request", done=True)
            yield error_chunk.to_json() + "\n"
    
    return StreamingResponse(
        stream_comparison_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no" 
        }
    )


@router.post("/chat_rwg")
async def chat_rwg(
    request: Request,
    message: str = Body(embed=True)
):
    """
    get stream response for related work generation
    """
    user_id = request.headers.get('X-User-ID')
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="User ID not found"
        )

    if user_id not in review_service.active_reviews:
        review_service.active_reviews[user_id] = {
            "comparison_messages": [],
            "rwg_messages": [],
            "files": []
        }
    
    async def stream_rwg_response():
        try:
            async for content_chunk, is_done in review_service.generate_rwg_response(user_id, message):
                response_chunk = ReviewResponseChunk(content=content_chunk, done=is_done)
                json_chunk = response_chunk.to_json() + "\n"
                yield json_chunk
        except Exception as e:
            logger.error(f"Error in stream_rwg_response: {str(e)}")
            error_chunk = ReviewResponseChunk(content="Error processing RWG request", done=True)
            yield error_chunk.to_json() + "\n"
    
    return StreamingResponse(
        stream_rwg_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no" 
        }
    )


@router.get("/comparison_messages")
async def get_comparison_messages(
    request: Request,
):
    """
    Get user's comparison history messages
    """
    user_id = request.headers.get('X-User-ID')
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="User ID not found"
        )
    messages = review_service.get_comparison_messages(user_id)
    return messages


@router.get("/rwg_messages")
async def get_rwg_messages(
    request: Request,
):
    """
    Get user's related work generation history messages
    """
    user_id = request.headers.get('X-User-ID')
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="User ID not found"
        )
    messages = review_service.get_rwg_messages(user_id)
    return messages


@router.get("/files")
async def get_review_files(
    request: Request
):
    """
    Get user's attached files for review
    """
    user_id = request.headers.get('X-User-ID')
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="User ID not found"
        )
    
    if user_id not in review_service.active_reviews:
        review_service.active_reviews[user_id] = {
            "comparison_messages": [],
            "rwg_messages": [],
            "files": []
        }
    
    review_data = review_service.active_reviews[user_id]
    result = []

    if review_data["files"]:
        for file_data in review_data["files"]:
            result.append({
                "file_path": file_data["file_path"],
                "filename": file_data["filename"],
                "paper_id": file_data["paper_id"],
                "paper_URL": file_data["paper_URL"],
                "added_at": file_data["added_at"]
            })
    
    return result 