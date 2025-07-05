import asyncio
import schedule
import time
import logging
import threading
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

from .database import SessionLocal, User, Strategy
from .portfolio_routes import sync_user_data
from .rebalancer import RebalancerEngine
from .notifications import NotificationService
from .analytics import PortfolioAnalytics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ScheduleFrequency(Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"

@dataclass
class ScheduledTask:
    """Represents a scheduled task"""
    id: str
    name: str
    frequency: ScheduleFrequency
    enabled: bool = True
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    user_id: Optional[int] = None
    strategy_id: Optional[int] = None

async def sync_all_users():
    """Sync portfolio data for all users with connected accounts"""
    db = SessionLocal()
    try:
        # Get all users with Plaid access tokens
        users = db.query(User).filter(User.plaid_access_token.isnot(None)).all()
        
        logger.info(f"Starting nightly sync for {len(users)} users")
        
        for user in users:
            try:
                logger.info(f"Syncing data for user {user.id}")
                await sync_user_data(user.id, user.plaid_access_token, db)
                logger.info(f"Successfully synced user {user.id}")
            except Exception as e:
                logger.error(f"Failed to sync user {user.id}: {str(e)}")
                
        logger.info("Nightly sync completed")
        
    except Exception as e:
        logger.error(f"Error in nightly sync: {str(e)}")
    finally:
        db.close()

def run_sync():
    """Wrapper to run async sync function"""
    asyncio.run(sync_all_users())

class AutomatedRebalancer:
    """Automated rebalancing scheduler and executor"""
    
    def __init__(self):
        self.is_running = False
        self.scheduler_thread = None
        self.tasks: Dict[str, ScheduledTask] = {}
        
    def start(self):
        """Start the automated rebalancing scheduler"""
        if self.is_running:
            return
            
        self.is_running = True
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()
        logger.info("Automated rebalancer started")
        
    def stop(self):
        """Stop the automated rebalancing scheduler"""
        self.is_running = False
        if self.scheduler_thread:
            self.scheduler_thread.join()
        logger.info("Automated rebalancer stopped")
        
    def _run_scheduler(self):
        """Main scheduler loop"""
        # Schedule periodic tasks
        schedule.every().day.at("09:00").do(self._daily_rebalancing_check)
        schedule.every().monday.at("08:00").do(self._weekly_portfolio_review)
        schedule.every().day.at("07:00").do(self._send_daily_notifications)
        schedule.every().hour.do(self._check_market_conditions)
        
        while self.is_running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
            
    def _daily_rebalancing_check(self):
        """Check all strategies for rebalancing needs"""
        logger.info("Starting daily rebalancing check")
        
        db = SessionLocal()
        try:
            rebalancer = RebalancerEngine(db)
            notification_service = NotificationService(db)
            
            # Get all active strategies
            strategies = db.query(Strategy).all()
            
            for strategy in strategies:
                try:
                    # Check if rebalancing is needed
                    trades = rebalancer.calculate_trades(strategy.user_id, strategy.id)
                    
                    if trades:
                        # Execute trades if auto-rebalancing is enabled
                        if self._is_auto_rebalancing_enabled(strategy.user_id):
                            success = rebalancer.execute_rebalancing(strategy.user_id, strategy.id)
                            if success:
                                logger.info(f"Auto-rebalanced strategy {strategy.id} for user {strategy.user_id}")
                            else:
                                logger.error(f"Failed to auto-rebalance strategy {strategy.id}")
                        else:
                            # Send notification instead
                            alerts = notification_service.check_rebalancing_alerts(strategy.user_id)
                            if alerts:
                                notification_service.send_rebalancing_alert(strategy.user_id, alerts)
                                
                except Exception as e:
                    logger.error(f"Error checking strategy {strategy.id}: {e}")
                    
        finally:
            db.close()
            
    def _weekly_portfolio_review(self):
        """Weekly portfolio performance review"""
        logger.info("Starting weekly portfolio review")
        
        db = SessionLocal()
        try:
            analytics = PortfolioAnalytics(db)
            notification_service = NotificationService(db)
            
            # Get all users with active accounts
            users = db.query(User).filter(User.plaid_access_token.isnot(None)).all()
            
            for user in users:
                try:
                    # Generate weekly performance report
                    metrics = analytics.calculate_performance_metrics(user.id, 7)
                    
                    if metrics:
                        # Check for significant changes
                        if abs(metrics.total_return) > 0.05:  # 5% change
                            self._send_performance_alert(user.id, metrics)
                            
                except Exception as e:
                    logger.error(f"Error reviewing portfolio for user {user.id}: {e}")
                    
        finally:
            db.close()
            
    def _send_daily_notifications(self):
        """Send daily portfolio summaries"""
        logger.info("Sending daily notifications")
        
        db = SessionLocal()
        try:
            notification_service = NotificationService(db)
            results = notification_service.process_all_notifications()
            logger.info(f"Notification results: {results}")
            
        finally:
            db.close()
            
    def _check_market_conditions(self):
        """Check market conditions and adjust strategies if needed"""
        logger.info("Checking market conditions")
        
        db = SessionLocal()
        try:
            # Get market data and check for volatility spikes
            # This would integrate with market data provider
            
            # For now, just log the check
            logger.info("Market conditions check completed")
            
        finally:
            db.close()
            
    def _is_auto_rebalancing_enabled(self, user_id: int) -> bool:
        """Check if user has auto-rebalancing enabled"""
        # This would check user preferences
        # For now, return False to avoid automatic trading
        return False
        
    def _send_performance_alert(self, user_id: int, metrics):
        """Send performance alert for significant changes"""
        db = SessionLocal()
        try:
            notification_service = NotificationService(db)
            
            alerts = [{
                "type": "weekly_performance",
                "value": metrics.total_return,
                "message": f"Weekly portfolio return: {metrics.total_return:.2%}",
                "severity": "HIGH" if abs(metrics.total_return) > 0.1 else "MEDIUM"
            }]
            
            notification_service.send_performance_alert(user_id, alerts)
            
        finally:
            db.close()
            
    def add_custom_task(self, task: ScheduledTask):
        """Add a custom scheduled task"""
        self.tasks[task.id] = task
        logger.info(f"Added custom task: {task.name}")
        
    def remove_custom_task(self, task_id: str):
        """Remove a custom scheduled task"""
        if task_id in self.tasks:
            del self.tasks[task_id]
            logger.info(f"Removed custom task: {task_id}")
            
    def get_scheduled_tasks(self) -> List[ScheduledTask]:
        """Get all scheduled tasks"""
        return list(self.tasks.values())
        
    def get_next_run_times(self) -> Dict[str, datetime]:
        """Get next run times for all scheduled jobs"""
        next_runs = {}
        for job in schedule.jobs:
            next_runs[str(job.job_func)] = job.next_run
        return next_runs

# Global scheduler instance
automated_rebalancer = AutomatedRebalancer()

def start_scheduler():
    """Start the background scheduler"""
    logger.info("Starting portfolio sync scheduler and automated rebalancer")
    
    # Start automated rebalancer
    automated_rebalancer.start()
    
    # Schedule nightly sync at 2 AM
    schedule.every().day.at("02:00").do(run_sync)
    
    # For testing, also allow manual trigger every hour
    # schedule.every().hour.do(run_sync)
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    start_scheduler()