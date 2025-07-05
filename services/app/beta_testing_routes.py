"""Beta testing API routes"""
from fastapi import APIRouter, HTTPException, Depends, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from .auth import get_current_user
from .beta_testing import (
    beta_testing_manager, 
    BetaTestPhase, 
    BetaUserStatus, 
    FeedbackType, 
    BetaTestSeverity,
    BetaUser,
    BetaFeedback
)
from .database import get_db
from .models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/beta", tags=["beta_testing"])

# Request/Response Models
class BetaSessionRequest(BaseModel):
    user_agent: Optional[str] = None
    device_type: Optional[str] = None
    browser: Optional[str] = None

class BetaSessionResponse(BaseModel):
    session_id: str
    message: str

class BetaActionRequest(BaseModel):
    action: str
    context: Dict[str, Any] = Field(default_factory=dict)

class BetaFeedbackRequest(BaseModel):
    feedback_type: FeedbackType
    severity: BetaTestSeverity
    title: str = Field(..., max_length=255)
    description: str = Field(..., max_length=5000)
    feature_area: Optional[str] = None
    url: Optional[str] = None
    screenshot_url: Optional[str] = None
    reproduction_steps: Optional[str] = None

class BetaFeedbackResponse(BaseModel):
    feedback_id: int
    message: str

class BetaUserRegistrationRequest(BaseModel):
    name: str = Field(..., max_length=255)
    email: str = Field(..., max_length=255)
    company: Optional[str] = None
    role: Optional[str] = None
    phone: Optional[str] = None
    timezone: Optional[str] = None
    testing_focus: Optional[List[str]] = None
    experience_level: Optional[str] = None
    portfolio_size: Optional[str] = None

class BetaMetricsResponse(BaseModel):
    timestamp: datetime
    phase: BetaTestPhase
    active_users: int
    total_sessions: int
    avg_session_duration: float
    error_rate: float
    response_time_p95: float
    user_satisfaction: float
    bugs_reported: int
    bugs_resolved: int
    features_tested: int

# Beta Session Management
@router.post("/session/start", response_model=BetaSessionResponse)
async def start_beta_session(
    request: Request,
    session_request: BetaSessionRequest,
    current_user: User = Depends(get_current_user)
):
    """Start a new beta testing session"""
    try:
        # Check if user is a beta user
        db = next(get_db())
        beta_user = db.query(BetaUser).filter(
            BetaUser.user_id == current_user.id,
            BetaUser.status == BetaUserStatus.ACTIVE
        ).first()
        
        if not beta_user:
            raise HTTPException(
                status_code=403,
                detail="User is not an active beta tester"
            )
        
        # Prepare session data
        session_data = {
            "user_agent": session_request.user_agent or request.headers.get("User-Agent"),
            "ip_address": request.client.host if request.client else None,
            "device_type": session_request.device_type,
            "browser": session_request.browser
        }
        
        # Start session
        session_id = beta_testing_manager.start_beta_session(beta_user.id, session_data)
        
        return BetaSessionResponse(
            session_id=session_id,
            message="Beta testing session started successfully"
        )
        
    except Exception as e:
        logger.error(f"Failed to start beta session: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to start beta testing session"
        )

@router.post("/session/{session_id}/end")
async def end_beta_session(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """End a beta testing session"""
    try:
        beta_testing_manager.end_beta_session(session_id)
        return {"message": "Beta testing session ended successfully"}
        
    except Exception as e:
        logger.error(f"Failed to end beta session: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to end beta testing session"
        )

@router.post("/session/{session_id}/action")
async def track_beta_action(
    session_id: str,
    action_request: BetaActionRequest,
    current_user: User = Depends(get_current_user)
):
    """Track user action during beta session"""
    try:
        beta_testing_manager.track_user_action(
            session_id, 
            action_request.action, 
            action_request.context
        )
        return {"message": "Action tracked successfully"}
        
    except Exception as e:
        logger.error(f"Failed to track beta action: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to track user action"
        )

# Beta Feedback Management
@router.post("/feedback", response_model=BetaFeedbackResponse)
async def submit_beta_feedback(
    feedback_request: BetaFeedbackRequest,
    current_user: User = Depends(get_current_user)
):
    """Submit beta testing feedback"""
    try:
        # Check if user is a beta user
        db = next(get_db())
        beta_user = db.query(BetaUser).filter(
            BetaUser.user_id == current_user.id,
            BetaUser.status == BetaUserStatus.ACTIVE
        ).first()
        
        if not beta_user:
            raise HTTPException(
                status_code=403,
                detail="User is not an active beta tester"
            )
        
        # Submit feedback
        feedback_data = feedback_request.dict()
        feedback_id = beta_testing_manager.submit_feedback(beta_user.id, feedback_data)
        
        return BetaFeedbackResponse(
            feedback_id=feedback_id,
            message="Feedback submitted successfully"
        )
        
    except Exception as e:
        logger.error(f"Failed to submit beta feedback: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to submit feedback"
        )

@router.get("/feedback")
async def get_beta_feedback(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    feedback_type: Optional[FeedbackType] = None,
    severity: Optional[BetaTestSeverity] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get beta feedback (admin only for now)"""
    try:
        db = next(get_db())
        
        # Check if user is a beta user
        beta_user = db.query(BetaUser).filter(
            BetaUser.user_id == current_user.id
        ).first()
        
        if not beta_user:
            raise HTTPException(
                status_code=403,
                detail="User is not a beta tester"
            )
        
        # Build query
        query = db.query(BetaFeedback).filter(
            BetaFeedback.beta_user_id == beta_user.id
        )
        
        if feedback_type:
            query = query.filter(BetaFeedback.feedback_type == feedback_type)
        if severity:
            query = query.filter(BetaFeedback.severity == severity)
        if status:
            query = query.filter(BetaFeedback.status == status)
        
        # Get feedback with pagination
        feedback = query.offset(skip).limit(limit).all()
        
        return {
            "feedback": [
                {
                    "id": fb.id,
                    "type": fb.feedback_type.value,
                    "severity": fb.severity.value,
                    "title": fb.title,
                    "description": fb.description,
                    "status": fb.status,
                    "feature_area": fb.feature_area,
                    "url": fb.url,
                    "created_at": fb.created_at.isoformat(),
                    "updated_at": fb.updated_at.isoformat(),
                    "resolved_at": fb.resolved_at.isoformat() if fb.resolved_at else None
                }
                for fb in feedback
            ],
            "total": query.count()
        }
        
    except Exception as e:
        logger.error(f"Failed to get beta feedback: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve feedback"
        )

# Beta User Management
@router.post("/register")
async def register_beta_user(
    registration_request: BetaUserRegistrationRequest,
    current_user: User = Depends(get_current_user)
):
    """Register as a beta user"""
    try:
        db = next(get_db())
        
        # Check if user is already registered
        existing_beta_user = db.query(BetaUser).filter(
            BetaUser.user_id == current_user.id
        ).first()
        
        if existing_beta_user:
            raise HTTPException(
                status_code=400,
                detail="User is already registered for beta testing"
            )
        
        # Create beta user
        beta_user = BetaUser(
            user_id=current_user.id,
            email=registration_request.email,
            name=registration_request.name,
            company=registration_request.company,
            role=registration_request.role,
            phone=registration_request.phone,
            timezone=registration_request.timezone,
            testing_focus=','.join(registration_request.testing_focus) if registration_request.testing_focus else None,
            experience_level=registration_request.experience_level,
            portfolio_size=registration_request.portfolio_size,
            phase=BetaTestPhase.INTERNAL,  # Start with internal phase
            status=BetaUserStatus.INVITED
        )
        
        db.add(beta_user)
        db.commit()
        
        logger.info(f"Registered beta user: {beta_user.id}")
        
        return {
            "message": "Successfully registered for beta testing",
            "beta_user_id": beta_user.id,
            "phase": beta_user.phase.value,
            "status": beta_user.status.value
        }
        
    except Exception as e:
        logger.error(f"Failed to register beta user: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to register for beta testing"
        )

@router.post("/activate")
async def activate_beta_user(
    current_user: User = Depends(get_current_user)
):
    """Activate beta user account"""
    try:
        db = next(get_db())
        
        beta_user = db.query(BetaUser).filter(
            BetaUser.user_id == current_user.id,
            BetaUser.status == BetaUserStatus.INVITED
        ).first()
        
        if not beta_user:
            raise HTTPException(
                status_code=404,
                detail="Beta user invitation not found"
            )
        
        beta_user.status = BetaUserStatus.ACTIVE
        beta_user.activated_at = datetime.utcnow()
        
        db.commit()
        
        logger.info(f"Activated beta user: {beta_user.id}")
        
        return {
            "message": "Beta user account activated successfully",
            "phase": beta_user.phase.value,
            "status": beta_user.status.value
        }
        
    except Exception as e:
        logger.error(f"Failed to activate beta user: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to activate beta user account"
        )

# Beta Metrics and Analytics
@router.get("/metrics", response_model=BetaMetricsResponse)
async def get_beta_metrics(
    phase: Optional[BetaTestPhase] = None,
    current_user: User = Depends(get_current_user)
):
    """Get beta testing metrics"""
    try:
        # Check if user is a beta user (for now, allow all beta users to see metrics)
        db = next(get_db())
        beta_user = db.query(BetaUser).filter(
            BetaUser.user_id == current_user.id
        ).first()
        
        if not beta_user:
            raise HTTPException(
                status_code=403,
                detail="User is not a beta tester"
            )
        
        # Get metrics
        metrics = beta_testing_manager.get_beta_metrics(phase)
        
        return BetaMetricsResponse(
            timestamp=metrics.timestamp,
            phase=metrics.phase,
            active_users=metrics.active_users,
            total_sessions=metrics.total_sessions,
            avg_session_duration=metrics.avg_session_duration,
            error_rate=metrics.error_rate,
            response_time_p95=metrics.response_time_p95,
            user_satisfaction=metrics.user_satisfaction,
            bugs_reported=metrics.bugs_reported,
            bugs_resolved=metrics.bugs_resolved,
            features_tested=metrics.features_tested
        )
        
    except Exception as e:
        logger.error(f"Failed to get beta metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve beta metrics"
        )

@router.get("/leaderboard")
async def get_beta_leaderboard(
    limit: int = Query(10, ge=1, le=50),
    current_user: User = Depends(get_current_user)
):
    """Get beta user leaderboard"""
    try:
        # Check if user is a beta user
        db = next(get_db())
        beta_user = db.query(BetaUser).filter(
            BetaUser.user_id == current_user.id
        ).first()
        
        if not beta_user:
            raise HTTPException(
                status_code=403,
                detail="User is not a beta tester"
            )
        
        # Get leaderboard
        leaderboard = beta_testing_manager.get_user_leaderboard(limit)
        
        return {
            "leaderboard": leaderboard,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get beta leaderboard: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve beta leaderboard"
        )

@router.get("/status")
async def get_beta_status(
    current_user: User = Depends(get_current_user)
):
    """Get current user's beta testing status"""
    try:
        db = next(get_db())
        
        beta_user = db.query(BetaUser).filter(
            BetaUser.user_id == current_user.id
        ).first()
        
        if not beta_user:
            return {
                "is_beta_user": False,
                "message": "User is not registered for beta testing"
            }
        
        return {
            "is_beta_user": True,
            "beta_user_id": beta_user.id,
            "phase": beta_user.phase.value,
            "status": beta_user.status.value,
            "invited_at": beta_user.invited_at.isoformat(),
            "activated_at": beta_user.activated_at.isoformat() if beta_user.activated_at else None,
            "total_sessions": beta_user.total_sessions,
            "total_session_time": beta_user.total_session_time,
            "last_login": beta_user.last_login.isoformat() if beta_user.last_login else None
        }
        
    except Exception as e:
        logger.error(f"Failed to get beta status: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve beta status"
        )

# Admin endpoints (these would need proper admin authentication in production)
@router.get("/admin/export")
async def export_beta_data(
    format: str = Query("json", regex="^(json)$"),
    current_user: User = Depends(get_current_user)
):
    """Export beta testing data (admin only)"""
    try:
        # For now, allow any beta user to export (in production, would need admin check)
        db = next(get_db())
        beta_user = db.query(BetaUser).filter(
            BetaUser.user_id == current_user.id
        ).first()
        
        if not beta_user:
            raise HTTPException(
                status_code=403,
                detail="User is not a beta tester"
            )
        
        # Export data
        export_data = beta_testing_manager.export_beta_data(format)
        
        return JSONResponse(
            content=export_data,
            headers={"Content-Disposition": f"attachment; filename=beta_data_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"}
        )
        
    except Exception as e:
        logger.error(f"Failed to export beta data: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to export beta data"
        )