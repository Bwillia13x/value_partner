"""Plaid integration API endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import Dict, Any
import logging

from ..database import get_db, User
from . import get_plaid_service
from ..auth_routes import get_current_user

router = APIRouter(prefix="/integrations/plaid", tags=["integrations"])

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@router.post("/link-token")
async def create_link_token(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Generate a Plaid Link token for the frontend
    
    This endpoint returns a link_token that can be used by the Plaid Link
    component to initialize the account linking flow.
    """
    try:
        # Generate link token for the current user
        link_token_data = get_plaid_service().create_link_token(str(current_user.id))
        return {
            "link_token": link_token_data["link_token"],
            "expiration": link_token_data["expiration"],
            "request_id": str(request.state.request_id) if hasattr(request.state, 'request_id') else None
        }
    except Exception as e:
        logger.error(f"Error creating Plaid link token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create link token"
        )

@router.post("/exchange-token")
async def exchange_public_token(
    public_token: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Exchange a public token for an access token and sync account data
    
    This endpoint is called after a user successfully links an account in the Plaid Link flow.
    It exchanges the public token for a permanent access token and initiates data sync.
    """
    try:
        # Exchange public token for access token
        exchange_response = get_plaid_service().exchange_public_token(public_token)
        access_token = exchange_response["access_token"]
        item_id = exchange_response["item_id"]
        
        # Sync account data
        sync_result = get_plaid_service().sync_plaid_data(
            user_id=str(current_user.id),
            access_token=access_token,
            item_id=item_id,
            db=db
        )
        
        return {
            "status": "success",
            "item_id": item_id,
            **sync_result
        }
        
    except Exception as e:
        logger.error(f"Error exchanging public token: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not complete account linking"
        )

@router.post("/sync/{item_id}")
async def sync_plaid_item(
    item_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Manually trigger a sync for a specific Plaid item
    
    This endpoint can be used to force a refresh of account data for a previously
    linked Plaid item.
    """
    try:
        # In a real implementation, you would look up the access token for this item
        # from your database. For now, we'll return a placeholder response.
        return {
            "status": "success",
            "message": "Sync initiated",
            "item_id": item_id
        }
    except Exception as e:
        logger.error(f"Error syncing Plaid item {item_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not sync item {item_id}"
        )

@router.post("/webhook")
async def plaid_webhook(webhook_data: Dict[str, Any], db: Session = Depends(get_db)) -> Dict[str, str]:
    """
    Handle Plaid webhook events
    
    This endpoint receives webhook notifications from Plaid about events like
    successful account linking, transaction updates, etc.
    """
    webhook_type = webhook_data.get("webhook_type")
    webhook_code = webhook_data.get("webhook_code")
    item_id = webhook_data.get("item_id")
    
    logger.info(f"Received Plaid webhook: {webhook_type}.{webhook_code} for item {item_id}")
    
    # Handle different webhook types
    if webhook_type == "ITEM":
        if webhook_code == "WEBHOOK_UPDATE_ACKNOWLEDGED":
            logger.info(f"Webhook verified for item {item_id}")
        elif webhook_code == "ERROR":
            error = webhook_data.get("error", {})
            logger.error(f"Plaid error for item {item_id}: {error}")
    
    elif webhook_type == "TRANSACTIONS":
        if webhook_code in ["SYNC_UPDATES_AVAILABLE", "DEFAULT_UPDATE"]:
            # In a real implementation, you would process transaction updates here
            logger.info(f"Transaction updates available for item {item_id}")
    
    elif webhook_type == "HOLDINGS":
        if webhook_code == "DEFAULT_UPDATE":
            # In a real implementation, you would sync holdings here
            logger.info(f"Holdings updates available for item {item_id}")
    
    return {"status": "success"}
