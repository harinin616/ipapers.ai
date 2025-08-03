# app/routers/folders.py
from fastapi import APIRouter, Header, HTTPException, Depends, status, Path, Request, Response, Query
from typing import List, Optional
from pydantic import BaseModel

from app.services.db_service import db_service   # 你之前的单例
from app.services.chat_service import chat_service  # 你的 chat_service 单例
from app.services.llm_service import llm_service  # 你的 LLM 服务单例
router = APIRouter()

# ────────────── Pydantic Output Schema ──────────────
class FileOut(BaseModel):
    paper_id:  str
    platform: str = "arxiv"
    filename:  str
    paper_URL: str
    added_at:  str
    selected: bool

class FolderOut(BaseModel):
    id:    int
    name:  str
    files: List[FileOut]

@router.get("", response_model=List[FolderOut])
async def list_folders(request: Request):
    """
    返回当前用户所有文件夹及其文件
    格式符合前端 api.get_user_folders()
    """
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(status_code=401, detail="X-User-ID header missing")
    if user_id.isdigit():
        user_id=await db_service.get_uuid_by_user_id(int(user_id))
    folders = await db_service.get_folders_with_files(user_id)
    # [
    #   { "id": 3, "name": "default",
    #     "files": [
    #       { "paper_id": "...", "filename": "...", "paper_URL": "...", "added_at": "..."},
    #       ...
    #     ]
    #   }, ...
    # ]
    return folders


class RenamePayload(BaseModel):
    folder_id: int
    name: str

@router.patch("/rename", status_code=204)
async def rename_folder(
    request: Request,
    payload: RenamePayload,
):
    user_id = request.headers.get("X-User-ID")
    if user_id.isdigit():
        user_id=await db_service.get_uuid_by_user_id(int(user_id))
    ok, msg = await db_service.rename_folder(
        user_id=user_id,
        folder_id=payload.folder_id,
        new_name=payload.name,
    )
    if not ok:
        # msg 里放的是人可读的原因
        raise HTTPException(status_code=400, detail=msg)
    return {"ok": True}

class AttachPayload(BaseModel):
    paper_id: str
    platform: Optional[str] = "arxiv"

@router.post("/{folder_id}/files", status_code=204)
async def attach_paper_to_folder(
    folder_id: int,
    payload: AttachPayload
):
    """Attach a paper to the given folder."""
    ok = await db_service.add_file_to_folder(
        folder_id=folder_id,
        paper_id=payload.paper_id,
        platform=payload.platform
    )
    if not ok:
        raise HTTPException(400, "attach failed")


@router.delete(
    "/{folder_id}/files/{paper_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove a paper from a folder"
)
async def remove_paper_from_folder(
    request: Request,
    folder_id: int = Path(..., description="Folder ID"),
    paper_id: str = Path(..., description="Paper ID"),
    platform: str = Query("arxiv", description="Paper platform"),
):
    # 从请求头获取当前用户
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID missing or invalid"
        )
    if user_id.isdigit():
        user_id=await db_service.get_uuid_by_user_id(int(user_id))
    ok = await db_service.remove_file_from_folder(
        user_id=user_id,
        folder_id=folder_id,
        paper_id=paper_id,
        platform=platform
    )
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to remove paper from folder"
        )

    # FastAPI 会用 204 返回
    return Response(status_code=status.HTTP_204_NO_CONTENT)

class CreateFolderPayload(BaseModel):
    name: str



# 2）定义给前端返回的 schema
class CreateFolderOut(BaseModel):
    id: int
    name: str
    file_count: int



@router.post(
    "/",
    response_model=CreateFolderOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_folder(
    request: Request,
    payload: CreateFolderPayload
):
    # 从请求头里取 user_id
    uid = request.headers.get("X-User-ID")
    if uid.isdigit():
        uid=await db_service.get_uuid_by_user_id(int(uid))
    #print(f"[create_folder] X-User-ID: {uid}")

    if not uid:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing or invalid X-User-ID")
    id = uid

    try:
        # 调用 service 层创建
        folder = await db_service.create_folder(user_id=id, name=payload.name)
    except Exception:
        logger.exception(f"[create_folder] failed for user={id}, name={payload.name}")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Internal Server Error")

    if not folder:
        # 比如重名又不想返回已有，也算创建失败
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Could not create folder")

    # 3）手动构造要返回给客户端的内容
    return {
        "id": folder.id,
        "name": folder.name,
        "file_count": 0  # 新建的肯定是 0
    }


@router.delete("/{folder_id}", status_code=204)
async def delete_folder(request: Request, folder_id: int):
    """
    Delete a folder (and all its files) belonging to the current user.
    """
    user_id = request.headers.get("X-User-ID")

    if not user_id:
        raise HTTPException(401, "User ID not found")

    if user_id.isdigit():
        user_id=await db_service.get_uuid_by_user_id(int(user_id))
  

    ok = await db_service.delete_folder(user_id, folder_id)
    if not ok:
        raise HTTPException(404, "Folder not found or not yours")

    # 204 No Content
    return Response(status_code=204)

@router.get("/{folder_id}/files")
async def get_files_by_folderId(
    folder_id: int,
):
    files = await db_service.get_files_by_folder_id(folder_id)
    if not files:
        return []
   # print(files)
    return files

@router.get("/{folder_id}/summary")
async def get_folder_summary(
    folder_id: int,
):
    summary = await db_service.get_folder_summary(folder_id)

    return {"summary": summary} 


@router.post("/{folder_id}/summary/regenerate")
async def regenerate_folder_summary(
    folder_id: int,
):
    try:
        tmp=await db_service.get_files_by_folder_id(folder_id)
        message="please summarize the following files together in one paragraph. When mentioning specific papers, use citations in the format [1], [2], etc., where the number corresponds to the order of the papers below:\n"+ "".join(
            f"Paper id: [{i+1}] Title: {file['title']}\nAbstract: {file['abstract']}\n" for i, file in enumerate(tmp)
        )
        api_messages = [
            {"role": "system", "content": "You are a helpful assistant that summarizes academic papers."},
            {"role": "user", "content": message}
        ]
        summary = await llm_service.get_conversation_completion_non_streaming(
            messages=api_messages
        )
        await db_service.add_folder_summary(folder_id, summary)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    # 返回生成的摘要
    return {"summary": summary}