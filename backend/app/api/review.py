from fastapi import APIRouter, HTTPException, Body, Path, Request, Query
from fastapi.responses import StreamingResponse
from typing import Optional, List
import logging
import json
from pydantic import BaseModel

from app.services.review_service import review_service
from app.services.chat_service import chat_service

logger = logging.getLogger(__name__)

router = APIRouter()


class StreamRwsRequest(BaseModel):
    session_id: str
    message: str
    selected_files: List[str] = []


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


# ============ SESSION MANAGEMENT ENDPOINTS ============

@router.get("/sessions")
async def get_rws_sessions(request: Request):
    """
    Get user's RWS sessions list
    """
    user_id = request.headers.get('X-User-ID')
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")
    return review_service.get_sessions(user_id)


@router.post("/sessions")
async def create_rws_session(request: Request, data: dict = Body(...)):
    """
    Create new RWS session
    """
    user_id = request.headers.get('X-User-ID')
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")
    title = data.get("title", "Untitled RWS Session")
    session_id = review_service.create_session(user_id, title)
    return {"id": session_id, "title": title}


@router.delete("/sessions")
async def delete_rws_session(request: Request, data: dict = Body(...)):
    """
    Delete RWS session
    """
    user_id = request.headers.get('X-User-ID')
    session_id = data.get("session_id")
    if not user_id or not session_id:
        raise HTTPException(status_code=400, detail="Missing user_id or session_id")
    review_service.delete_session(user_id, session_id)
    return {"success": True}


@router.post("/update_session_title")
async def update_rws_session_title(
    request: Request,
    data: dict = Body(...)
):
    """
    Update RWS session title
    """
    user_id = request.headers.get('X-User-ID')
    session_id = data.get("session_id")
    title = data.get("title")
    if not user_id or not session_id or not title:
        raise HTTPException(status_code=400, detail="Missing user_id, session_id or title")
    success = review_service.update_session_title(user_id, session_id, title)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True}


@router.get("/messages")
async def get_rws_messages(
    request: Request,
    session_id: str = Query(...)
):
    """
    Get user's RWS history messages for a specific session
    """
    user_id = request.headers.get('X-User-ID')
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="User ID not found"
        )
    messages = review_service.get_messages(user_id, session_id)
    return messages


@router.post("/stream_rws")
async def stream_rws(
    request: Request,
    body: StreamRwsRequest
):
    """
    Get stream response for related work generation with session support
    """
    user_id = request.headers.get('X-User-ID')
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="User ID not found"
        )
    
    session_id = body.session_id
    message = body.message
    selected_files = body.selected_files

    # Ensure chat service has user data structure
    if user_id not in chat_service.active_chats:
        chat_service.active_chats[user_id] = {
            "files": [],
            "sessions": {}
        }
    
    # Update file selections if provided
    if selected_files and chat_service.active_chats[user_id]["files"]:
        for file in chat_service.active_chats[user_id]["files"]:
            if file["paper_id"] in selected_files:
                file["selected"] = True
            else:
                file["selected"] = False
    
    async def stream_rws_response():
        try:
            async for content_chunk, is_done in review_service.generate_rwg_response(user_id, message, session_id):
                response_chunk = ReviewResponseChunk(content=content_chunk, done=is_done)
                json_chunk = response_chunk.to_json() + "\n"
                yield json_chunk
        except Exception as e:
            logger.error(f"Error in stream_rws_response: {str(e)}")
            error_chunk = ReviewResponseChunk(content="Error processing RWS request", done=True)
            yield error_chunk.to_json() + "\n"
    
    return StreamingResponse(
        stream_rws_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no" 
        }
    )


# ============ GRAPH MANAGEMENT ENDPOINTS ============

@router.get("/graph")
async def get_paper_graph(request: Request):
    """
    Get the paper relation graph for the user
    """
    user_id = request.headers.get('X-User-ID')
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")
    
    graph = review_service.get_paper_graph(user_id)
    return graph


@router.post("/graph/nodes")
async def update_graph_nodes(request: Request, papers: List[dict] = Body(...)):
    """
    Update graph nodes based on user's papers
    """
    user_id = request.headers.get('X-User-ID')
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")
    
    success = review_service.update_graph_nodes(user_id, papers)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update graph nodes")
    
    return {"success": True}


@router.post("/graph/edges")
async def add_graph_edge(request: Request, data: dict = Body(...)):
    """
    Add a directed edge between two papers
    """
    user_id = request.headers.get('X-User-ID')
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")
    
    from_paper = data.get("from")
    to_paper = data.get("to")
    relationship_type = data.get("relationship_type", "relates_to")
    description = data.get("description", "")
    
    if not from_paper or not to_paper:
        raise HTTPException(status_code=400, detail="Missing from or to paper")
    
    success = review_service.add_graph_edge(user_id, from_paper, to_paper, relationship_type, description)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to add edge")
    
    return {"success": True}


@router.delete("/graph/edges")
async def remove_graph_edge(request: Request, data: dict = Body(...)):
    """
    Remove a directed edge between two papers
    """
    user_id = request.headers.get('X-User-ID')
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")
    
    from_paper = data.get("from")
    to_paper = data.get("to")
    
    if not from_paper or not to_paper:
        raise HTTPException(status_code=400, detail="Missing from or to paper")
    
    success = review_service.remove_graph_edge(user_id, from_paper, to_paper)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to remove edge")
    
    return {"success": True}


# ============ LEGACY ENDPOINTS (for backward compatibility) ============

@router.get("/rwg_messages")
async def get_rwg_messages(
    request: Request,
):
    """
    Get user's related work generation history messages (legacy endpoint)
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
    Get stream response for related work generation (legacy endpoint - uses default session)
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
            # Use default session for legacy compatibility
            async for content_chunk, is_done in review_service.generate_rwg_response(user_id, message, "default"):
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
