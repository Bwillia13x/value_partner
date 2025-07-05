from fastapi import APIRouter, Request, HTTPException, BackgroundTasks
from .database import get_db, User
from .portfolio_routes import sync_user_data
import hashlib
import hmac
import json
import logging
import os

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

PLAID_WEBHOOK_SECRET = os.getenv("PLAID_WEBHOOK_SECRET")

def verify_webhook_signature(request_body: bytes, signature: str) -> bool:
    """Verify webhook signature from Plaid"""
    if not PLAID_WEBHOOK_SECRET:
        raise ValueError("PLAID_WEBHOOK_SECRET environment variable must be set for webhook security")
    
    if not signature:
        return False
    
    expected_signature = hmac.new(
        PLAID_WEBHOOK_SECRET.encode(),
        request_body,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)

@router.post("/plaid")
async def plaid_webhook(
    request: Request,
    background_tasks: BackgroundTasks
):
    """Handle Plaid webhooks for account updates"""
    try:
        # Get raw body and signature
        body = await request.body()
        signature = request.headers.get("plaid-verification", "")
        
        # Verify signature
        if not verify_webhook_signature(body, signature):
            raise HTTPException(status_code=401, detail="Invalid signature")
        
        # Parse webhook data
        webhook_data = json.loads(body)
        webhook_type = webhook_data.get("webhook_type")
        webhook_code = webhook_data.get("webhook_code")
        item_id = webhook_data.get("item_id")
        
        logging.info(f"Received webhook: {webhook_type}/{webhook_code} for item {item_id}")
        
        # Handle different webhook types
        if webhook_type == "TRANSACTIONS":
            await handle_transactions_webhook(webhook_data, background_tasks)
        elif webhook_type == "HOLDINGS":
            await handle_holdings_webhook(webhook_data, background_tasks)
        elif webhook_type == "ITEM":
            await handle_item_webhook(webhook_data, background_tasks)
        else:
            logging.warning(f"Unhandled webhook type: {webhook_type}")
        
        return {"status": "ok"}
        
    except Exception as e:
        logging.error(f"Error processing webhook: {str(e)}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")

async def handle_transactions_webhook(webhook_data: dict, background_tasks: BackgroundTasks):
    """Handle transaction update webhooks"""
    webhook_code = webhook_data.get("webhook_code")
    item_id = webhook_data.get("item_id")
    
    if webhook_code in ["SYNC_UPDATES_AVAILABLE", "DEFAULT_UPDATE", "HISTORICAL_UPDATE"]:
        # Find user by item_id and sync data
        db = next(get_db())
        try:
            user = db.query(User).filter(User.plaid_item_id == item_id).first()
            if user and user.plaid_access_token:
                logging.info(f"Syncing transactions for user {user.id}")
                background_tasks.add_task(sync_user_data, user.id, user.plaid_access_token, db)
        finally:
            db.close()

async def handle_holdings_webhook(webhook_data: dict, background_tasks: BackgroundTasks):
    """Handle holdings update webhooks"""
    webhook_code = webhook_data.get("webhook_code")
    item_id = webhook_data.get("item_id")
    
    if webhook_code == "DEFAULT_UPDATE":
        # Find user by item_id and sync holdings
        db = next(get_db())
        try:
            user = db.query(User).filter(User.plaid_item_id == item_id).first()
            if user and user.plaid_access_token:
                logging.info(f"Syncing holdings for user {user.id}")
                background_tasks.add_task(sync_user_data, user.id, user.plaid_access_token, db)
        finally:
            db.close()

async def handle_item_webhook(webhook_data: dict, background_tasks: BackgroundTasks):
    """Handle item-level webhooks"""
    webhook_code = webhook_data.get("webhook_code")
    item_id = webhook_data.get("item_id")
    
    if webhook_code == "ERROR":
        # Handle item errors
        error = webhook_data.get("error", {})
        logging.error(f"Item error for {item_id}: {error}")
        
        # Could implement user notification here
        # For now, just log the error
        
    elif webhook_code == "PENDING_EXPIRATION":
        # Handle pending expiration
        logging.warning(f"Item {item_id} has pending expiration")
        
        # Could implement user notification to re-authenticate
        
    elif webhook_code == "USER_PERMISSION_REVOKED":
        # Handle permission revocation
        logging.info(f"User revoked permissions for item {item_id}")
        
        # Deactivate accounts for this item
        db = next(get_db())
        try:
            user = db.query(User).filter(User.plaid_item_id == item_id).first()
            if user:
                # Could mark accounts as inactive
                logging.info(f"Deactivating accounts for user {user.id}")
        finally:
            db.close()

@router.get("/test")
async def test_webhook():
    """Test endpoint to verify webhook setup"""
    return {"status": "webhook endpoint active"}