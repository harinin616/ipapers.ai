# app/api/ideas.py
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import json
from app.services.idea_service import get_idea_service

class Persona(BaseModel):
    key: str
    name: str
    on: bool

class GenerateIdeasRequest(BaseModel):
    topic: str
    rounds: int
    reviewers: int
    personas: List[Persona]

class Idea(BaseModel):
    id: str
    title: str
    summary: str
    novelty: int
    feasibility: int
    clarity: int
    score: int
    tags: List[str]

class GenerateIdeasResponse(BaseModel):
    ideas: List[Idea]
    kpis: Optional[dict] = None

class ExpandRequest(BaseModel):
    id: str

class ExpandResponse(BaseModel):
    markdown: str

router = APIRouter()
_service = get_idea_service()

def sse_event(event: str, data: dict) -> str:
    return f"event: {event}\n" + "data: " + json.dumps(data, ensure_ascii=False) + "\n\n"

@router.post("/generate", response_model=GenerateIdeasResponse)
async def generate(req: GenerateIdeasRequest):
    result = await _service.generate_ideas(req)
    return GenerateIdeasResponse(**result)

@router.post("/stream_generate")
async def stream_generate(req: GenerateIdeasRequest):
    async def gen():
        # ===== preamble: help proxies flush early =====
        yield ":" + (" " * 2048) + "\n\n"      # padding for some proxies
        yield "retry: 15000\n\n"               # SSE reconnection hint
        # ===== stages =====
        async for ev in _service.generate_ideas_stream(req):
            yield sse_event(ev.get("event", "phase"), ev)
    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",  # nginx: disable proxy buffering
    }
    return StreamingResponse(gen(), media_type="text/event-stream; charset=utf-8", headers=headers)

@router.post("/expand", response_model=ExpandResponse)
async def expand(req: ExpandRequest):
    md = await _service.expand_proposal(req.id)
    return ExpandResponse(markdown=md)
