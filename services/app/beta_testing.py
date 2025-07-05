"""Beta testing infrastructure and monitoring"""
import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import asyncio
from collections import defaultdict, deque
import uuid

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session
from sqlalchemy.sql import func

from .database import Base, get_db, User
from .monitoring import app_monitor, MetricsCollector

logger = logging.getLogger(__name__)

class BetaTestPhase(Enum):
    INTERNAL = "internal"
    CLOSED = "closed"
    OPEN = "open"
    COMPLETED = "completed"

class BetaUserStatus(Enum):
    INVITED = "invited"
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    COMPLETED = "completed"

class FeedbackType(Enum):
    BUG_REPORT = "bug_report"
    FEATURE_REQUEST = "feature_request"
    USABILITY_ISSUE = "usability_issue"
    PERFORMANCE_ISSUE = "performance_issue"
    GENERAL_FEEDBACK = "general_feedback"

class BetaTestSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

@dataclass
class BetaTestMetrics:
    """Beta testing metrics"""
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
    
class BetaUser(Base):
    """Beta testing user model"""
    __tablename__ = "beta_users"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    email = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    company = Column(String(255), nullable=True)
    role = Column(String(100), nullable=True)
    
    # Beta program details
    phase = Column(SQLEnum(BetaTestPhase), nullable=False)
    status = Column(SQLEnum(BetaUserStatus), default=BetaUserStatus.INVITED)
    invited_at = Column(DateTime, default=func.now())
    activated_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Testing profile
    testing_focus = Column(String(500), nullable=True)  # JSON array of focus areas
    experience_level = Column(String(50), nullable=True)  # beginner, intermediate, advanced
    portfolio_size = Column(String(50), nullable=True)  # small, medium, large
    
    # Contact and communication
    phone = Column(String(20), nullable=True)
    preferred_contact = Column(String(20), default="email")  # email, phone, both
    timezone = Column(String(50), nullable=True)
    
    # Tracking
    last_login = Column(DateTime, nullable=True)
    total_sessions = Column(Integer, default=0)
    total_session_time = Column(Float, default=0.0)  # in seconds
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationships
    user = relationship("User")
    feedback = relationship("BetaFeedback", back_populates="beta_user")
    test_sessions = relationship("BetaTestSession", back_populates="beta_user")

class BetaFeedback(Base):
    """Beta testing feedback model"""
    __tablename__ = "beta_feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    beta_user_id = Column(Integer, ForeignKey("beta_users.id"), nullable=False)
    
    # Feedback details
    feedback_type = Column(SQLEnum(FeedbackType), nullable=False)
    severity = Column(SQLEnum(BetaTestSeverity), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    
    # Context
    feature_area = Column(String(100), nullable=True)
    user_agent = Column(String(500), nullable=True)
    url = Column(String(500), nullable=True)
    screenshot_url = Column(String(500), nullable=True)
    reproduction_steps = Column(Text, nullable=True)
    
    # Status tracking
    status = Column(String(50), default="open")  # open, in_progress, resolved, closed
    assigned_to = Column(String(100), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    resolved_at = Column(DateTime, nullable=True)
    
    # Relationships
    beta_user = relationship("BetaUser", back_populates="feedback")

class BetaTestSession(Base):
    """Beta testing session tracking"""
    __tablename__ = "beta_test_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    beta_user_id = Column(Integer, ForeignKey("beta_users.id"), nullable=False)
    
    # Session details
    session_id = Column(String(100), unique=True, nullable=False)
    start_time = Column(DateTime, default=func.now())
    end_time = Column(DateTime, nullable=True)
    duration = Column(Float, nullable=True)  # in seconds
    
    # Activity tracking
    pages_visited = Column(Integer, default=0)
    actions_performed = Column(Integer, default=0)
    errors_encountered = Column(Integer, default=0)
    
    # Technical details
    user_agent = Column(String(500), nullable=True)
    ip_address = Column(String(45), nullable=True)
    device_type = Column(String(50), nullable=True)
    browser = Column(String(100), nullable=True)
    
    # Relationships
    beta_user = relationship("BetaUser", back_populates="test_sessions")

class BetaTestingManager:
    """Manager for beta testing operations"""
    
    def __init__(self):
        self.metrics_collector = MetricsCollector(max_metrics=50000)
        self.active_sessions = {}
        self.current_phase = BetaTestPhase.INTERNAL
        
    def start_beta_session(self, beta_user_id: int, session_data: Dict[str, Any]) -> str:
        """Start a new beta testing session"""
        session_id = str(uuid.uuid4())
        
        db = next(get_db())
        try:
            # Create session record
            session = BetaTestSession(
                beta_user_id=beta_user_id,
                session_id=session_id,
                user_agent=session_data.get("user_agent"),
                ip_address=session_data.get("ip_address"),
                device_type=session_data.get("device_type"),
                browser=session_data.get("browser")
            )
            db.add(session)
            
            # Update user last login
            beta_user = db.query(BetaUser).filter(BetaUser.id == beta_user_id).first()
            if beta_user:
                beta_user.last_login = datetime.utcnow()
                beta_user.total_sessions += 1
                
            db.commit()
            
            # Track in memory
            self.active_sessions[session_id] = {
                "beta_user_id": beta_user_id,
                "start_time": datetime.utcnow(),
                "actions": 0,
                "pages": 0,
                "errors": 0
            }
            
            logger.info(f"Started beta session {session_id} for user {beta_user_id}")
            return session_id
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to start beta session: {e}")
            raise
        finally:
            db.close()
    
    def end_beta_session(self, session_id: str):
        """End a beta testing session"""
        if session_id not in self.active_sessions:
            logger.warning(f"Session {session_id} not found in active sessions")
            return
            
        session_data = self.active_sessions.pop(session_id)
        end_time = datetime.utcnow()
        duration = (end_time - session_data["start_time"]).total_seconds()
        
        db = next(get_db())
        try:
            # Update session record
            session = db.query(BetaTestSession).filter(
                BetaTestSession.session_id == session_id
            ).first()
            
            if session:
                session.end_time = end_time
                session.duration = duration
                session.pages_visited = session_data["pages"]
                session.actions_performed = session_data["actions"]
                session.errors_encountered = session_data["errors"]
                
                # Update user total session time
                beta_user = db.query(BetaUser).filter(
                    BetaUser.id == session_data["beta_user_id"]
                ).first()
                if beta_user:
                    beta_user.total_session_time += duration
                    
                db.commit()
                
                logger.info(f"Ended beta session {session_id}, duration: {duration:.2f}s")
                
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to end beta session: {e}")
        finally:
            db.close()
    
    def track_user_action(self, session_id: str, action: str, context: Dict[str, Any]):
        """Track user action during beta session"""
        if session_id in self.active_sessions:
            self.active_sessions[session_id]["actions"] += 1
            
            # Track specific action types
            if action == "page_visit":
                self.active_sessions[session_id]["pages"] += 1
            elif action == "error":
                self.active_sessions[session_id]["errors"] += 1
                
            # Store in metrics collector
            self.metrics_collector.record_event(
                "beta_user_action",
                {
                    "session_id": session_id,
                    "action": action,
                    "context": context,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
    
    def submit_feedback(self, beta_user_id: int, feedback_data: Dict[str, Any]) -> int:
        """Submit feedback from beta user"""
        db = next(get_db())
        try:
            feedback = BetaFeedback(
                beta_user_id=beta_user_id,
                feedback_type=FeedbackType(feedback_data["feedback_type"]),
                severity=BetaTestSeverity(feedback_data["severity"]),
                title=feedback_data["title"],
                description=feedback_data["description"],
                feature_area=feedback_data.get("feature_area"),
                user_agent=feedback_data.get("user_agent"),
                url=feedback_data.get("url"),
                screenshot_url=feedback_data.get("screenshot_url"),
                reproduction_steps=feedback_data.get("reproduction_steps")
            )
            
            db.add(feedback)
            db.commit()
            
            logger.info(f"Submitted feedback {feedback.id} from beta user {beta_user_id}")
            
            # Send notification for critical issues
            if feedback.severity == BetaTestSeverity.CRITICAL:
                self._send_critical_feedback_alert(feedback)
                
            return feedback.id
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to submit feedback: {e}")
            raise
        finally:
            db.close()
    
    def get_beta_metrics(self, phase: Optional[BetaTestPhase] = None) -> BetaTestMetrics:
        """Get current beta testing metrics"""
        db = next(get_db())
        try:
            # Base query
            query = db.query(BetaUser)
            if phase:
                query = query.filter(BetaUser.phase == phase)
            
            # Calculate metrics
            total_users = query.count()
            active_users = query.filter(BetaUser.status == BetaUserStatus.ACTIVE).count()
            
            # Session metrics
            session_query = db.query(BetaTestSession)
            if phase:
                session_query = session_query.join(BetaUser).filter(BetaUser.phase == phase)
                
            total_sessions = session_query.count()
            avg_duration = session_query.filter(
                BetaTestSession.duration.isnot(None)
            ).with_entities(func.avg(BetaTestSession.duration)).scalar() or 0
            
            # Feedback metrics
            feedback_query = db.query(BetaFeedback)
            if phase:
                feedback_query = feedback_query.join(BetaUser).filter(BetaUser.phase == phase)
                
            total_feedback = feedback_query.count()
            bugs_reported = feedback_query.filter(
                BetaFeedback.feedback_type == FeedbackType.BUG_REPORT
            ).count()
            bugs_resolved = feedback_query.filter(
                BetaFeedback.feedback_type == FeedbackType.BUG_REPORT,
                BetaFeedback.status == "resolved"
            ).count()
            
            # System metrics from monitoring
            system_metrics = app_monitor.get_system_metrics()
            
            return BetaTestMetrics(
                timestamp=datetime.utcnow(),
                phase=phase or self.current_phase,
                active_users=active_users,
                total_sessions=total_sessions,
                avg_session_duration=avg_duration,
                error_rate=system_metrics.get("error_rate", 0.0),
                response_time_p95=system_metrics.get("response_time_p95", 0.0),
                user_satisfaction=self._calculate_user_satisfaction(phase),
                bugs_reported=bugs_reported,
                bugs_resolved=bugs_resolved,
                features_tested=self._count_features_tested(phase)
            )
            
        finally:
            db.close()
    
    def _calculate_user_satisfaction(self, phase: Optional[BetaTestPhase]) -> float:
        """Calculate user satisfaction score"""
        # This would integrate with survey results
        # For now, return a placeholder based on feedback sentiment
        return 4.2  # Placeholder
    
    def _count_features_tested(self, phase: Optional[BetaTestPhase]) -> int:
        """Count number of features tested"""
        # This would track feature usage across sessions
        # For now, return a placeholder
        return 25  # Placeholder
    
    def _send_critical_feedback_alert(self, feedback: BetaFeedback):
        """Send alert for critical feedback"""
        # This would integrate with notification system
        logger.critical(f"Critical feedback received: {feedback.title}")
        
    def get_user_leaderboard(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get beta user leaderboard by activity"""
        db = next(get_db())
        try:
            users = db.query(BetaUser).order_by(
                BetaUser.total_sessions.desc(),
                BetaUser.total_session_time.desc()
            ).limit(limit).all()
            
            leaderboard = []
            for user in users:
                feedback_count = db.query(BetaFeedback).filter(
                    BetaFeedback.beta_user_id == user.id
                ).count()
                
                leaderboard.append({
                    "name": user.name,
                    "company": user.company,
                    "total_sessions": user.total_sessions,
                    "total_time": user.total_session_time,
                    "feedback_count": feedback_count,
                    "last_login": user.last_login.isoformat() if user.last_login else None
                })
                
            return leaderboard
            
        finally:
            db.close()
    
    def export_beta_data(self, format: str = "json") -> str:
        """Export beta testing data for analysis"""
        db = next(get_db())
        try:
            # Get all beta data
            users = db.query(BetaUser).all()
            feedback = db.query(BetaFeedback).all()
            sessions = db.query(BetaTestSession).all()
            
            export_data = {
                "export_timestamp": datetime.utcnow().isoformat(),
                "summary": {
                    "total_users": len(users),
                    "total_feedback": len(feedback),
                    "total_sessions": len(sessions)
                },
                "users": [
                    {
                        "id": user.id,
                        "name": user.name,
                        "company": user.company,
                        "phase": user.phase.value,
                        "status": user.status.value,
                        "total_sessions": user.total_sessions,
                        "total_time": user.total_session_time,
                        "invited_at": user.invited_at.isoformat(),
                        "last_login": user.last_login.isoformat() if user.last_login else None
                    }
                    for user in users
                ],
                "feedback": [
                    {
                        "id": fb.id,
                        "type": fb.feedback_type.value,
                        "severity": fb.severity.value,
                        "title": fb.title,
                        "description": fb.description,
                        "status": fb.status,
                        "created_at": fb.created_at.isoformat(),
                        "resolved_at": fb.resolved_at.isoformat() if fb.resolved_at else None
                    }
                    for fb in feedback
                ],
                "sessions": [
                    {
                        "id": session.id,
                        "user_id": session.beta_user_id,
                        "duration": session.duration,
                        "pages_visited": session.pages_visited,
                        "actions_performed": session.actions_performed,
                        "errors_encountered": session.errors_encountered,
                        "start_time": session.start_time.isoformat(),
                        "end_time": session.end_time.isoformat() if session.end_time else None
                    }
                    for session in sessions
                ]
            }
            
            if format == "json":
                return json.dumps(export_data, indent=2)
            else:
                raise ValueError(f"Unsupported export format: {format}")
                
        finally:
            db.close()

# Global beta testing manager
beta_testing_manager = BetaTestingManager()

def get_beta_testing_manager() -> BetaTestingManager:
    """Get the global beta testing manager"""
    return beta_testing_manager