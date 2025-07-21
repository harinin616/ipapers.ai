# app/routers/forum.py
from __future__ import annotations

import base64, hashlib, secrets
from datetime import datetime, timezone
from typing import List
import uuid

from fastapi import (
    APIRouter, Depends, Header, HTTPException, Request, Response, status
)
from pydantic import BaseModel, Field

from app.services.db_service import db_service
from app.models.db_models import DBSharedFolder, DBFolder

router = APIRouter()

class ShareFolderInPayload(BaseModel):
    folder_id : int
    is_public : bool  = True


@router.post(
    "/",
)
async def create_shared_folder(
    payload : ShareFolderInPayload,
    user_id : str | None = Header(None, alias="X-User-ID"),
):
  #  print(f"create_shared_folder: {payload=}, {user_id=}")
    if not user_id:
        raise HTTPException(401, "X-User-ID header missing")

    # 若前端还发旧的数字型 id，先转换
    if str(user_id).isdigit():
        user_id = await db_service.get_uuid_by_user_id(int(user_id))

    folder: DBFolder | None = await db_service.get_folder(payload.folder_id)
    if not folder or str(folder.user_id) != user_id:
        raise HTTPException(404, "Folder not found")

    await db_service.create_shared_folder(
        folder_id = payload.folder_id,
        owner_id  = user_id,
        is_public = payload.is_public,
    )

    return {"ok": True}   

class SharedFolderOut(BaseModel):
    id         : int
    folder_id  : int
    owner_id   : uuid.UUID
    is_public  : bool
    created_at : datetime
    folder_name: str
    file_cnt   : int

@router.get(
    "/",
    response_model=List[SharedFolderOut],
)
async def get_shared_folders(
):
    shared_folders = await db_service.get_shared_folders()
    return shared_folders

@router.delete(
    "/{folder_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a shared folder"
)
async def delete_shared_folder(
    folder_id: int,
):
    try:
        ok = await db_service.delete_shared_folder(folder_id)
        if not ok:
            raise HTTPException(404, "Shared folder not found or you do not have permission to delete it")
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)