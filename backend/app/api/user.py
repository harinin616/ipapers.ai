import uuid
from fastapi import APIRouter, Request, HTTPException, Body
from app.services.db_service import db_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/get_id")
async def generate_user_id():
    """
    Generate a unique user ID.
    """
    user_id = uuid.uuid4()
    return str(user_id)

@router.get("/subscription-status")
async def get_subscription_status(request: Request):
    """
    Get user's subscription status for daily feed emails.
    Requires authentication.
    """
    user_id = request.headers.get('X-User-ID')
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        user_id = int(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    
    subscription_status = await db_service.get_user_subscription_status(user_id)
    
    if subscription_status is None:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "user_id": user_id,
        "subscribed": subscription_status
    }

@router.post("/subscription")
async def update_subscription(request: Request, data: dict = Body(...)):
    """
    Update user's subscription status for daily feed emails.
    Requires authentication.
    
    Body parameters:
    - subscribed: boolean - new subscription status
    """
    user_id = request.headers.get('X-User-ID')
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    try:
        user_id = int(user_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user ID")
    
    subscribed = data.get("subscribed")
    if subscribed is None:
        raise HTTPException(status_code=400, detail="Missing 'subscribed' parameter")
    
    if not isinstance(subscribed, bool):
        raise HTTPException(status_code=400, detail="'subscribed' must be a boolean")
    
    success = await db_service.update_user_subscription(user_id, subscribed)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update subscription status")
    
    status_text = "subscribed to" if subscribed else "unsubscribed from"
    logger.info(f"User {user_id} successfully {status_text} daily feed")
    
    return {
        "success": True,
        "user_id": user_id,
        "subscribed": subscribed,
        "message": f"Successfully {status_text} daily feed"
    }
