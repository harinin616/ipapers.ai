# app/routers/topics.py
from fastapi import APIRouter, Depends, Header, HTTPException, status,Request
from pydantic import BaseModel
from typing import Optional, List
from app.services.db_service import db_service          # 你的 DBService 单例

router = APIRouter()

# -------- Pydantic request / response --------
class TopicIn(BaseModel):
    topic: str

class TopicsOut(BaseModel):
    topics: List[str]

# -------- 获取当前用户 id 的简单依赖 --------
async def get_current_user_id(x_user_id: Optional[str] = Header(None)):
    if not x_user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="X-User-ID header missing")
    try:
        return int(x_user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid X-User-ID")


# =============== ROUTES ===============

@router.get("/", response_model=TopicsOut)
async def list_topics(request: Request):
    uid = request.headers.get("X-User-ID")
    if uid.isdigit():
        uid=await db_service.get_uuid_by_user_id(int(uid))
    topics = await db_service.get_topics_by_user(uid)   # 之前补充的函数
    return {"topics": topics}

@router.post("/", status_code=201)
async def add_topic(request: Request,body: TopicIn):
    uid = request.headers.get("X-User-ID")
    if uid.isdigit():
        uid=await db_service.get_uuid_by_user_id(int(uid))
    ok = await db_service.add_topic_to_user(uid, body.topic.strip())
    if not ok:
        raise HTTPException(status_code=500, detail="DB insert failed")
    return {"ok": True}

@router.delete("/{topic}")
async def delete_topic(request: Request, topic: str):
    uid = request.headers.get("X-User-ID")
    if uid.isdigit():
        uid=await db_service.get_uuid_by_user_id(int(uid))
    ok = await db_service.remove_topic_from_user(uid, topic)
    if not ok:
        raise HTTPException(status_code=404, detail="topic not found")
    return {"ok": True}
