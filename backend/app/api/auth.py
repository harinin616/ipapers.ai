from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
import requests
from app.services.db_service import db_service
import uuid
import os
from app.services.chat_service import chat_service

router = APIRouter()


class TokenPayload(BaseModel):
    credential: str

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")

@router.post("/google-login")
async def google_login(request: Request, payload: TokenPayload):
    resp = requests.get(
        "https://oauth2.googleapis.com/tokeninfo",
        params={"id_token": payload.credential}
    )

    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        user_id = uuid.uuid4()

    info = resp.json()

    if info["aud"] != GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=403, detail="Token audience mismatch")
    
    user_email = info.get("email")
    user_name = info.get("name")
    picture = info.get("picture")
    tmp = await db_service.get_user_id_by_email(user_email)
    if tmp:
        user_id = tmp

    result = await db_service.add_user(user_id, user_name, user_email)
    if not result:
        raise HTTPException(status_code=500, detail="Failed to add user")

    await chat_service.load_user_history(user_id)
 
    return {
        "email": user_email,
        "name": user_name,
        "picture": picture,
        "user_id": user_id
    }
