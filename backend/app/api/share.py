# app/api/share.py
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

router = APIRouter()

# 简单内存存储，生产环境建议换成数据库或 Redis
_share_store: dict[str, List[str]] = {}

class ShareRequest(BaseModel):
    files: List[str]

class ShareResponse(BaseModel):
    share_id: str

class GetShareResponse(BaseModel):
    files: List[str]

@router.post("/", response_model=ShareResponse)
async def share_files(req: ShareRequest):
    # 生成一个短 ID
    share_id = uuid.uuid4().hex[:8]
    _share_store[share_id] = req.files
    return ShareResponse(share_id=share_id)

@router.get("/{share_id}", response_model=GetShareResponse)
async def get_shared(share_id: str):
    files = _share_store.get(share_id)
    if files is None:
        raise HTTPException(status_code=404, detail="Share not found")
    return GetShareResponse(files=files)
