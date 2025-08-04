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
async def get_subscription_status(email: str = None):
    """
    Get subscription status for an email address.
    
    Query parameters:
    - email: email address to check
    """
    if not email:
        raise HTTPException(status_code=400, detail="Email parameter is required")
    
    is_subscribed = await db_service.check_email_in_list(email)
    
    return {
        "email": email,
        "subscribed": is_subscribed
    }

@router.post("/subscription")
async def update_subscription(data: dict = Body(...)):
    """
    Update email subscription status for daily feed emails.
    
    Body parameters:
    - email: string - email address
    - subscribed: boolean - new subscription status
    """
    email = data.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Missing 'email' parameter")
    
    subscribed = data.get("subscribed")
    if subscribed is None:
        raise HTTPException(status_code=400, detail="Missing 'subscribed' parameter")
    
    if not isinstance(subscribed, bool):
        raise HTTPException(status_code=400, detail="'subscribed' must be a boolean")
    
    # Basic email validation
    email = email.strip().lower()
    if not email or '@' not in email:
        raise HTTPException(status_code=400, detail="Invalid email format")
    
    if subscribed:
        # Subscribe: add email to list
        success = await db_service.add_email_to_list(email)
        action = "subscribed to"
    else:
        # Unsubscribe: remove email from list
        success = await db_service.remove_email_from_list(email)
        action = "unsubscribed from"
    
    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to update subscription status")
    
    logger.info(f"Email {email} successfully {action} daily feed")
    
    return {
        "success": True,
        "email": email,
        "subscribed": subscribed,
        "message": f"Successfully {action} daily feed"
    }
