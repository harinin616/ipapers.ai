from fastapi import APIRouter, HTTPException, Body, Path, Request, Query
from fastapi.responses import StreamingResponse
from typing import Optional, List
import logging
import json
from app.services.chat_service import chat_service
from pydantic import BaseModel

class StreamChatRequest(BaseModel):
    session_id: str
    message: str
    #selected_files: List[str]

logger = logging.getLogger(__name__)

router = APIRouter()


class ChatResponseChunk:
    """
    Stream response chunk
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


@router.get("/messages")
async def get_chat_messages(
    request: Request,
    session_id: str = Query(...)
):
    """
    Get user's history messages
    """
    user_id = request.headers.get('X-User-ID')
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="User ID not found"
        )
    messages = []
    messages = chat_service.get_messages(user_id,session_id)
    return messages


@router.post("/stream_chat")
async def chat(
    request: Request,
    body: StreamChatRequest
):
    """
    get stream chat response
    """
    user_id = request.headers.get('X-User-ID')
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="User ID not found"
        )
    session_id = body.session_id
    message = body.message
   # selected_files = body.selected_files
    if user_id not in chat_service.active_chats:
        chat_service.active_chats[user_id] = {
            "files": [],
            "sessions": {}
        }
    
    #if chat_service.active_chats[user_id]["files"]:
     #   for file in chat_service.active_chats[user_id]["files"]:
      #      if file["paper_id"] in selected_files:
       #         file["selected"] = True
        #    else:
         #       file["selected"] = False
    
    async def stream_chat_response():
        try:
            async for content_chunk, is_done in chat_service.generate_response(user_id,session_id, message):
                response_chunk = ChatResponseChunk(content=content_chunk, done=is_done)
                json_chunk = response_chunk.to_json() + "\n"
                yield json_chunk
        except Exception as e:
            logger.error(f"Error in stream_chat_response: {str(e)}")
            error_chunk = ChatResponseChunk(content="Error processing request", done=True)
            yield error_chunk.to_json() + "\n"
    
    return StreamingResponse(
        stream_chat_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no" 
        }
    )


@router.get("/files")
async def get_user_files(
    request: Request
):
    """
    Get user's attached files
    """
    user_id = request.headers.get('X-User-ID')
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="User ID not found"
        )
    
    if user_id not in chat_service.active_chats:
       chat_service.active_chats[user_id] = {
            "files": [],
            "sessions": {}
        }
    
    chat_data = chat_service.active_chats[user_id]
    result = []

    if chat_data["files"]:
        for file_data in chat_data["files"]:
            result.append({
                "file_path": file_data["file_path"],
                "filename": file_data["filename"],
                "paper_id": file_data["paper_id"],
                "paper_URL": file_data["paper_URL"],
                "added_at": file_data["added_at"],
                "selected": file_data["selected"]
            })
    
    return result


@router.delete("/files/delete/{paper_id}")
async def delete_file(
    request: Request,
    paper_id: str = Path()
):
    """
    Delete a file from user's attached files
    """
    user_id = request.headers.get('X-User-ID')
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="User ID not found"
        )
    
    chat_data = chat_service.active_chats[user_id]
    
    if chat_data["files"]:
        for file_data in chat_data["files"]:
            if file_data["paper_id"] == paper_id:
                chat_data["files"].remove(file_data)
                return True
    
    return False

@router.post("/update_file_selection")
async def update_file_selection(request: Request, data: dict = Body(...)):
    user_id = request.headers.get('X-User-ID')
    paper_id = data.get("paper_id")
    selected = data.get("selected")
    if not user_id or paper_id is None or selected is None:
        raise HTTPException(status_code=400, detail="Missing parameters")
    files = chat_service.active_chats[user_id]["files"]
    for file in files:
        if file["paper_id"] == paper_id:
            file["selected"] = selected
            break
    return {"success": True}


@router.post("/get_paper")
async def get_paper(
    request: Request,
    paper_id: str = Body(embed=True)
):
    """
    Attach a paper to user, download the paper if not exists
    """
    user_id = request.headers.get('X-User-ID')
    if not user_id:
        raise HTTPException(    
            status_code=401,
            detail="User ID not found"
        )
    try:
        success = await chat_service.get_paper(user_id, paper_id)
        
        if not success:
            return False
        
        return True
    
    except Exception as e:
        logger.error(f"Error getting paper {paper_id} for chat session {user_id}: {str(e)}")
        return False
    
@router.post("/attach_paper")
async def attach_paper(
    request: Request,
    paper_id: str = Body(embed=True)
):
    """
    Get a paper from the database
    """
    user_id = request.headers.get('X-User-ID')
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="User ID not found"
        )
    await chat_service.attach_paper(user_id, paper_id)
    return True

@router.post("/process_embeddings")
async def process_paper_embeddings(
    request: Request,
    paper_id: str = Body(embed=True)
):
    """
    Process embeddings for a paper
    """

    user_id = request.headers.get('X-User-ID')
    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="User ID not found"
        )
    
    try:
        success = await chat_service.process_embeddings(paper_id)
        
        if not success:
            return False
        
        return True
    
    except Exception as e:
        logger.error(f"Error processing embeddings for paper {paper_id} for user {user_id}: {str(e)}")
        return False

@router.get("/sessions")
async def get_sessions(request: Request):
    """
    获取用户所有会话列表
    """
    user_id = request.headers.get('X-User-ID')
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")
    return chat_service.get_sessions(user_id)


@router.post("/sessions")
async def create_session(request: Request, data: dict = Body(...)):
    """
    新建会话
    """
    user_id = request.headers.get('X-User-ID')
    if not user_id:
        raise HTTPException(status_code=401, detail="User ID not found")
    title = data.get("title", "Untitled Session")
    session_id = chat_service.create_session(user_id, title)
    return {"id": session_id, "title": title}


@router.delete("/sessions")
async def delete_session(request: Request, data: dict = Body(...)):
    """
    删除会话
    """
    user_id = request.headers.get('X-User-ID')
    session_id = data.get("session_id")
    if not user_id or not session_id:
        raise HTTPException(status_code=400, detail="Missing user_id or session_id")
    chat_service.delete_session(user_id, session_id)
    return {"success": True}

@router.post("/update_session_title")
async def update_session_title(
    request: Request,
    data: dict = Body(...)
):
    """
    更新会话标题
    """
    user_id = request.headers.get('X-User-ID')
    session_id = data.get("session_id")
    title = data.get("title")
    if not user_id or not session_id or not title:
        raise HTTPException(status_code=400, detail="Missing user_id, session_id or title")
    success = chat_service.update_session_title(user_id, session_id, title)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True}