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
    request: Request,
):
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(status_code=401, detail="X-User-ID header missing")
    shared_folders = await db_service.get_shared_folders(user_id)
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


@router.get(
    "/{folder_id}/permission",
)
async def get_share_permission(
    folder_id: int,
):
    permission = await db_service.get_share_permission(folder_id)
    return permission


class ShareModeIn(BaseModel):
    is_public: bool

@router.patch("/{folder_id}/mode", summary="Update share mode of a folder")
async def update_share_mode(
    folder_id: int,
    payload: ShareModeIn,
):
    ok = await db_service.update_share_mode(folder_id, payload.is_public)
    if not ok:
        raise HTTPException(
            status_code=404,
            detail="Shared folder not found or you do not have permission to update it",
        )
    return {"ok": True}

@router.get("/{folder_id}/mode", summary="Get share mode of a folder")
async def get_share_mode(
    folder_id: int,
):
    is_public = await db_service.get_share_mode(folder_id)
    if is_public is None:
        raise HTTPException(
            status_code=404,
            detail="Shared folder not found or you do not have permission to access it",
        )
    return is_public


class ShareUserIn(BaseModel):
    email: str

@router.post("/{folder_id}/add_user", summary="Add a user to shared folder")
async def add_share_user(
    folder_id: int,
    payload: ShareUserIn,
):
    email = payload.email.strip()
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
    print(f"Adding user {email} to shared folder {folder_id}")
    
    user_id = await db_service.get_user_id_by_email(email)
    if not user_id:
        raise HTTPException(status_code=404, detail="User not found")
    print(f"User ID for {email} is {user_id}")

    ok = await db_service.add_share_user(folder_id, user_id)
    if not ok:
        raise HTTPException(
            status_code=404,
            detail="Shared folder not found or you do not have permission to add users",
        )

@router.delete("/{folder_id}/remove_user", summary="Remove a user from shared folder")
async def remove_share_user(
    folder_id: int,
    payload: ShareUserIn,
):
    email = payload.email.strip()
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")
    
    user_id = await db_service.get_user_id_by_email(email)
    if not user_id:
        raise HTTPException(status_code=404, detail="User not found")

    ok = await db_service.remove_share_user(folder_id, user_id)
    if not ok:
        raise HTTPException(
            status_code=404,
            detail="Shared folder not found or you do not have permission to remove users",
        )