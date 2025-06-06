from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
import requests

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

    
    return {
        "email": user_email,
        "name": user_name,
        "picture": picture
    }
