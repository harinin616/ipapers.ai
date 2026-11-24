import uuid
from fastapi import APIRouter, Request, HTTPException, Body
from app.services.db_service import db_service
from app.security import create_access_token
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

@router.post("/guest")
async def create_guest_session():
    """Issue a guest identity: a fresh user id plus a signed token that proves it on later requests."""
    user_id = str(uuid.uuid4())
    return {"user_id": user_id, "access_token": create_access_token(user_id)}


async def _require_own_email(request: Request, email: str) -> str:
    user_id = request.headers.get("X-User-ID")
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")
    own = await db_service.get_user_email(user_id)
    if not own or own.strip().lower() != (email or "").strip().lower():
        raise HTTPException(status_code=403, detail="You can only manage your own subscription")
    return own.strip().lower()


@router.get("/subscription-status")
async def get_subscription_status(request: Request, email: str = None):
    """
    Get subscription status for an email address.
    
    Query parameters:
    - email: email address to check
    """
    if not email:
        raise HTTPException(status_code=400, detail="Email parameter is required")
    await _require_own_email(request, email)
    
    is_subscribed = await db_service.check_email_in_list(email)
    
    return {
        "email": email,
        "subscribed": is_subscribed
    }

@router.post("/subscription")
async def update_subscription(request: Request, data: dict = Body(...)):
    """
    Update email subscription status for daily feed emails.
    
    Body parameters:
    - email: string - email address
    - subscribed: boolean - new subscription status
    """
    email = data.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Missing 'email' parameter")
    await _require_own_email(request, email)
    
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
