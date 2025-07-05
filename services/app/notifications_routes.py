from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Optional
from .database import get_db
from .notifications import NotificationService
from pydantic import BaseModel

router = APIRouter(prefix="/notifications", tags=["notifications"])


class AlertResponse(BaseModel):
    """Response model for alerts"""
    rebalancing: List[Dict]
    performance: List[Dict]


class NotificationRequest(BaseModel):
    """Request model for sending notifications"""
    user_id: int
    notification_type: str
    message: str
    email: Optional[bool] = True


class PreferencesRequest(BaseModel):
    """Request model for notification preferences"""
    email_enabled: bool = True
    rebalance_alerts: bool = True
    performance_reports: bool = True
    market_alerts: bool = False
    threshold_alerts: bool = True
    frequency: str = "daily"


@router.get("/alerts/{user_id}", response_model=AlertResponse)
async def get_user_alerts(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Get all current alerts for a user"""
    
    notification_service = NotificationService(db)
    alerts = notification_service.check_all_alerts(user_id)
    
    return AlertResponse(
        rebalancing=alerts["rebalancing"],
        performance=alerts["performance"]
    )


@router.post("/send/{user_id}")
async def send_notification(
    user_id: int,
    request: NotificationRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Send a specific notification to a user"""
    
    notification_service = NotificationService(db)
    
    if request.notification_type == "rebalancing":
        alerts = notification_service.check_rebalancing_alerts(user_id)
        if alerts:
            background_tasks.add_task(
                notification_service.send_rebalancing_alert,
                user_id,
                alerts
            )
    
    elif request.notification_type == "performance":
        alerts = notification_service.check_performance_alerts(user_id)
        if alerts:
            background_tasks.add_task(
                notification_service.send_performance_alert,
                user_id,
                alerts
            )
    
    elif request.notification_type == "daily_summary":
        background_tasks.add_task(
            notification_service.send_daily_summary,
            user_id
        )
    
    else:
        raise HTTPException(status_code=400, detail="Invalid notification type")
    
    return {"message": f"Notification queued for user {user_id}"}


@router.post("/send-all")
async def send_all_notifications(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Process and send all pending notifications"""
    
    notification_service = NotificationService(db)
    
    background_tasks.add_task(
        notification_service.process_all_notifications
    )
    
    return {"message": "All notifications queued for processing"}


@router.get("/preferences/{user_id}")
async def get_notification_preferences(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Get user's notification preferences"""
    
    # In a real implementation, this would fetch from a user_preferences table
    # For now, return default preferences
    
    return {
        "user_id": user_id,
        "email_enabled": True,
        "rebalance_alerts": True,
        "performance_reports": True,
        "market_alerts": False,
        "threshold_alerts": True,
        "frequency": "daily",
        "email_address": "user@example.com"  # Would come from User table
    }


@router.put("/preferences/{user_id}")
async def update_notification_preferences(
    user_id: int,
    preferences: PreferencesRequest,
    db: Session = Depends(get_db)
):
    """Update user's notification preferences"""
    
    # In a real implementation, this would update a user_preferences table
    
    return {
        "message": "Preferences updated successfully",
        "user_id": user_id,
        "preferences": preferences.dict()
    }


@router.get("/types")
async def get_notification_types():
    """Get available notification types"""
    
    types = [
        {
            "type": "rebalancing",
            "name": "Rebalancing Alerts",
            "description": "Alerts when portfolio drifts from target allocation"
        },
        {
            "type": "performance",
            "name": "Performance Alerts",
            "description": "Alerts for significant performance changes"
        },
        {
            "type": "daily_summary",
            "name": "Daily Summary",
            "description": "Daily portfolio performance summary"
        },
        {
            "type": "market_alerts",
            "name": "Market Alerts",
            "description": "General market condition alerts"
        }
    ]
    
    return {"notification_types": types}


@router.get("/history/{user_id}")
async def get_notification_history(
    user_id: int,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Get user's notification history"""
    
    # In a real implementation, this would fetch from a notifications_log table
    # For now, return mock data
    
    return {
        "user_id": user_id,
        "notifications": [
            {
                "id": 1,
                "type": "rebalancing",
                "title": "Portfolio Rebalancing Alert",
                "message": "Your portfolio has drifted from target allocation",
                "sent_at": "2024-01-15T10:30:00",
                "status": "delivered",
                "channel": "email"
            },
            {
                "id": 2,
                "type": "daily_summary",
                "title": "Daily Portfolio Summary",
                "message": "Your daily portfolio performance summary",
                "sent_at": "2024-01-15T08:00:00",
                "status": "delivered",
                "channel": "email"
            }
        ],
        "total_count": 2
    }


@router.post("/test/{user_id}")
async def send_test_notification(
    user_id: int,
    notification_type: str = "daily_summary",
    db: Session = Depends(get_db)
):
    """Send a test notification"""
    
    notification_service = NotificationService(db)
    
    try:
        if notification_type == "daily_summary":
            success = notification_service.send_daily_summary(user_id)
        elif notification_type == "rebalancing":
            # Create a test alert
            test_alerts = [{
                "type": "rebalance_drift",
                "strategy_name": "Test Strategy",
                "symbol": "AAPL",
                "current_weight": 0.15,
                "target_weight": 0.10,
                "drift": 0.05,
                "threshold": 0.03,
                "severity": "MEDIUM",
                "created_at": "2024-01-15T10:30:00"
            }]
            success = notification_service.send_rebalancing_alert(user_id, test_alerts)
        else:
            raise HTTPException(status_code=400, detail="Invalid test notification type")
        
        if success:
            return {"message": f"Test {notification_type} notification sent successfully"}
        else:
            raise HTTPException(status_code=500, detail="Failed to send test notification")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error sending test notification: {str(e)}")


@router.get("/settings")
async def get_notification_settings():
    """Get global notification settings"""
    
    return {
        "smtp_configured": bool(os.getenv("SMTP_USERNAME")),
        "default_frequency": "daily",
        "available_frequencies": ["daily", "weekly", "monthly"],
        "available_channels": ["email", "push", "sms"],
        "rate_limits": {
            "daily_summary": "1 per day",
            "rebalancing": "1 per hour",
            "performance": "3 per day"
        }
    }