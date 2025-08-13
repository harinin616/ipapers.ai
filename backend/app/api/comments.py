# app/api/comments.py
from fastapi import APIRouter, Depends, HTTPException, Query, status, Request,Body
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel, Field
from app.services.db_service import db_service
import datetime

router = APIRouter()

@router.get("/shared/{folderId}")
async def get_shared_comments(folderId: int):
    try:
        comments = await db_service.get_comments_by_folder_id(folderId)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return comments

@router.post("/shared")
async def add_shared_comment(
    request: Request,
    folderId: int = Body(...),
    content: str = Body(...)
):
    uid = request.headers.get("X-User-ID")
    try:
        comment = await db_service.add_comment_by_folder_id(uid, folderId, content)
        return comment
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/shared/{cid}")
async def delete_shared_comment(cid: int, request: Request):
    try:
        uid = request.headers.get("X-User-ID")
        ok = await db_service.delete_comment(cid, uid)
        if not ok:
            raise HTTPException(status_code=403, detail="Not allowed or comment not found")
        return {"message": "Comment deleted successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ===== Paper comments =====

@router.get("/paper/{paper_id}")
async def get_paper_comments(
    paper_id: str,
    platform: str = Query('arxiv')
):
    try:
        comments = await db_service.get_comments_by_paper_id(paper_id, platform)
        return comments
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/paper")
async def add_paper_comment(
    request: Request,
    paperId: str = Body(...),
    content: str = Body(...),
    platform: str = Body('arxiv')
):
    uid = request.headers.get("X-User-ID")
    try:
        comment = await db_service.add_comment_by_paper_id(uid, paperId, content, platform)
        if not comment:
            raise HTTPException(status_code=404, detail="Paper not found")
        return comment
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/paper/{cid}")
async def delete_paper_comment(cid: int, request: Request):
    try:
        uid = request.headers.get("X-User-ID")
        ok = await db_service.delete_comment(cid, uid)
        if not ok:
            raise HTTPException(status_code=403, detail="Not allowed or comment not found")
        return {"message": "Comment deleted successfully"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))