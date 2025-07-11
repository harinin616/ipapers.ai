# app/routers/folders.py
from fastapi import APIRouter, Header, HTTPException, Depends, status
from typing import List, Optional
from pydantic import BaseModel

from app.services.db_service import db_service   # 你之前的单例

router = APIRouter()

# ────────────── Pydantic Output Schema ──────────────
class FileOut(BaseModel):
    paper_id:  str
    filename:  str
    paper_URL: str
    added_at:  str

class FolderOut(BaseModel):
    id:    int
    name:  str
    files: List[FileOut]

# ────────────── 简易鉴权：取 X-User-ID Header ──────────────
async def get_current_user_id(x_user_id: Optional[str] = Header(None)) -> int:
    if not x_user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="X-User-ID header missing")
    try:
        return int(x_user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid X-User-ID")

# ────────────── 主要接口 ──────────────
@router.get("", response_model=List[FolderOut])
async def list_folders(user_id: int = Depends(get_current_user_id)):
    """
    返回当前用户所有文件夹及其文件
    格式符合前端 api.get_user_folders()
    """
    folders = await db_service.get_folders_with_files(user_id)
    # get_folders_with_files 应返回 python dict / ORM 对象列表:
    # [
    #   { "id": 3, "name": "default",
    #     "files": [
    #       { "paper_id": "...", "filename": "...", "paper_URL": "...", "added_at": "..."},
    #       ...
    #     ]
    #   }, ...
    # ]
    return folders
