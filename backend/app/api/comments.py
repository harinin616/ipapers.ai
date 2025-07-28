# app/api/comments.py
from fastapi import APIRouter, Depends, HTTPException, Query, status, Request,Body
from sqlalchemy.orm import Session
from typing import List

from pydantic import BaseModel, Field
from app.services.db_service import db_service

import datetime
router = APIRouter()


@router.get("/shared/{folderId}",)
async def get_shared_comments(
    folderId: int ,
):
    try:
        comments = await db_service.get_comments_by_folder_id(folderId)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return comments



@router.post(
    "/shared",
)
async def add_shared_comment(
    request: Request,
     folderId: int = Body(...),                    # ← 显式从 body 里取
    content: str = Body(...)
):
    uid = request.headers.get("X-User-ID")
    try:
        comment=await db_service.add_comment_by_folder_id(uid,folderId,content)
        return comment
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/shared/{cid}")
async def delete_shared_comment(
    cid: int,
):
    try:
        await db_service.delete_comment(cid)
        return {"message": "Comment deleted successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))