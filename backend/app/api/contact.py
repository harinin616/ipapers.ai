from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.db.database import get_async_db          # ← 你的 async Session 依赖
from app.models.db_models import DBFeedback

router = APIRouter()

# ---------- Pydantic ----------
class FeedbackIn(BaseModel):
    question: str = Field(..., max_length=500)
    email: str = Field(None, max_length=100)

class FeedbackOut(BaseModel):
    id: int
    created_at: datetime.datetime

# ---------- Endpoints ----------
@router.post(
    "/",
    response_model=FeedbackOut,
    status_code=status.HTTP_201_CREATED,
    summary="Submit feedback",
)
async def create_feedback(
    payload: FeedbackIn,
    db: AsyncSession = Depends(get_async_db),
):
    fb = DBFeedback(question=payload.question, email=payload.email)
    db.add(fb)
    await db.commit()
    await db.refresh(fb)
    return {"id": fb.id, "created_at": fb.created_at}


@router.get(
    "/",
    response_model=List[FeedbackIn],
    summary="List feedback (admin/debug)",
)
async def list_feedback(
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db),
):
    result = await db.execute(
        select(DBFeedback)
        .order_by(DBFeedback.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()
