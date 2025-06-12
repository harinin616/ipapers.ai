from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
import requests
from app.services.db_service import db_service
from app.services.chat_service import chat_service

router = APIRouter()

GOOGLE_CLIENT_ID = "500313985236-28j5sqcq0rte1eebccl6cs6k8f3rag3q.apps.googleusercontent.com"

class TokenPayload(BaseModel):
    credential: str


@router.post("/google-login")
async def google_login(payload: TokenPayload):
    resp = requests.get(
        "https://oauth2.googleapis.com/tokeninfo",
        params={"id_token": payload.credential}
    )

    if resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid token")

    info = resp.json()

    if info["aud"] != GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=403, detail="Token audience mismatch")
    
    user_email = info.get("email")
    user_name = info.get("name")
    picture = info.get("picture")

    result = await db_service.add_user(user_name, user_email)
    if not result:
        raise HTTPException(status_code=500, detail="Failed to add user")
    
    user_id = await db_service.get_user_id_by_email(user_email)
    if not user_id:
        raise HTTPException(status_code=500, detail="Failed to get user ID")

    user_id = str(user_id)   
    await chat_service.load_user_history(user_id)
 
    return {
        "email": user_email,
        "name": user_name,
        "picture": picture,
        "user_id": user_id
    }
