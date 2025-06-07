from fastapi import APIRouter, HTTPException, Body, Path, Request, Query
from fastapi.responses import StreamingResponse
from typing import Optional, List
import logging
import json

from app.services.review_service import review_service
from app.services.chat_service import chat_service

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
    messages = []
    messages = review_service.get_rwg_messages(user_id)
    return messages


@router.post("/chat_rwg")
async def chat_rwg(
    request: Request,
    message: str = Body(embed=True),
    selected_files: List[str] = Body(embed=True)
):
    """
    get stream response for related work generation (uses shared file system)
    """
    user_id = request.headers.get('X-User-ID')
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="User ID not found"
        )

    if user_id not in chat_service.active_chats:
        chat_service.active_chats[user_id] = {
            "messages": [],
            "files": []
        }
    if selected_files and chat_service.active_chats[user_id]["files"]:
        for file in chat_service.active_chats[user_id]["files"]:
            if file["paper_id"] in selected_files:
                file["selected"] = True
            else:
                file["selected"] = False
    
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
