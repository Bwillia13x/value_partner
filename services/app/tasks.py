"""Background tasks for data reconciliation and synchronization"""
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any
from celery import Celery

from .database import SessionLocal, User, Account, Holding, Transaction
from .integrations.plaid_service import PlaidService
from .alpaca_service import AlpacaService
from .notifications import NotificationService
from .analytics import PortfolioAnalytics

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Celery
celery_app = Celery(
    'value_partner_tasks',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_routes={
        'services.app.tasks.sync_all_accounts': {'queue': 'data_sync'},
        'services.app.tasks.reconcile_portfolio': {'queue': 'reconciliation'},
        'services.app.tasks.send_daily_reports': {'queue': 'notifications'},
    },
    beat_schedule={
        'daily-account-sync': {
            'task': 'services.app.tasks.sync_all_accounts',
            'schedule': 30.0,  # Every 30 seconds for demo (change to daily in production)
        },
        'daily-reconciliation': {
            'task': 'services.app.tasks.reconcile_all_portfolios',
            'schedule': 60.0,  # Every minute for demo (change to daily in production)
        },
        'daily-reports': {
            'task': 'services.app.tasks.send_daily_reports',
            'schedule': 300.0,  # Every 5 minutes for demo (change to daily in production)
        },
    }
)

@celery_app.task(bind=True, max_retries=3)
def sync_user_accounts(self, user_id: int) -> Dict[str, Any]:
    """Sync all accounts for a specific user"""
    logger.info(f"Starting account sync for user {user_id}")
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"error": f"User {user_id} not found"}
        
        results = {
            "user_id": user_id,
            "plaid_sync": None,
            "alpaca_sync": None,
            "errors": []
        }
        
        # Sync Plaid accounts
        if user.plaid_access_token:
            try:
                plaid_service = PlaidService()
                plaid_result = plaid_service.sync_accounts(user.plaid_access_token, db, user_id)
                results["plaid_sync"] = plaid_result
                logger.info(f"Plaid sync completed for user {user_id}")
            except Exception as e:
                error_msg = f"Plaid sync failed for user {user_id}: {str(e)}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
                
        # Sync Alpaca accounts (if user has Alpaca token)
        alpaca_token = getattr(user, 'alpaca_access_token', None)
        if alpaca_token:
            try:
                alpaca_service = AlpacaService()
                alpaca_result = alpaca_service.sync_account_data(db, user_id)
                results["alpaca_sync"] = alpaca_result
                logger.info(f"Alpaca sync completed for user {user_id}")
            except Exception as e:
                error_msg = f"Alpaca sync failed for user {user_id}: {str(e)}"
                logger.error(error_msg)
                results["errors"].append(error_msg)
                
        db.commit()
        return results
        
    except Exception as e:
        db.rollback()
        logger.error(f"Account sync failed for user {user_id}: {e}")
        # Retry the task
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying account sync for user {user_id} (attempt {self.request.retries + 1})")
            raise self.retry(countdown=60 * (2 ** self.request.retries))  # Exponential backoff
        return {"error": str(e)}
    finally:
        db.close()

@celery_app.task
def sync_all_accounts() -> Dict[str, Any]:
    """Sync accounts for all users"""
    logger.info("Starting sync for all user accounts")
    
    db = SessionLocal()
    try:
        # Get all users with connected accounts
        users = db.query(User).filter(
            (User.plaid_access_token.isnot(None)) |
            (User.alpaca_access_token.isnot(None))
        ).all()
        
        results = {
            "total_users": len(users),
            "successful_syncs": 0,
            "failed_syncs": 0,
            "errors": []
        }
        
        for user in users:
            try:
                # Queue individual user sync
                sync_result = sync_user_accounts.delay(user.id)
                results["successful_syncs"] += 1
                logger.info(f"Queued sync for user {user.id}")
            except Exception as e:
                results["failed_syncs"] += 1
                error_msg = f"Failed to queue sync for user {user.id}: {str(e)}"
                results["errors"].append(error_msg)
                logger.error(error_msg)
                
        logger.info(f"Sync queued for {results['successful_syncs']} users")
        return results
        
    except Exception as e:
        logger.error(f"Failed to sync all accounts: {e}")
        return {"error": str(e)}
    finally:
        db.close()

@celery_app.task(bind=True, max_retries=3)
def reconcile_portfolio(self, user_id: int) -> Dict[str, Any]:
    """Reconcile portfolio data for a user"""
    logger.info(f"Starting portfolio reconciliation for user {user_id}")
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"error": f"User {user_id} not found"}
            
        analytics = PortfolioAnalytics(db)
        
        # Get all accounts for the user
        accounts = db.query(Account).filter(Account.user_id == user_id).all()
        
        reconciliation_results = {
            "user_id": user_id,
            "accounts_processed": 0,
            "total_portfolio_value": 0.0,
            "discrepancies": [],
            "recommendations": []
        }
        
        for account in accounts:
            try:
                # Get holdings for account
                holdings = db.query(Holding).filter(Holding.account_id == account.id).all()
                
                account_value = sum(h.market_value or 0 for h in holdings)
                reconciliation_results["total_portfolio_value"] += account_value
                
                # Check for discrepancies
                if abs(account.current_balance - account_value) > 1.0:  # $1 tolerance
                    reconciliation_results["discrepancies"].append({
                        "account_id": account.id,
                        "account_name": account.name,
                        "reported_balance": account.current_balance,
                        "calculated_value": account_value,
                        "difference": account.current_balance - account_value
                    })
                    
                reconciliation_results["accounts_processed"] += 1
                
            except Exception as e:
                logger.error(f"Error processing account {account.id}: {e}")
                
        # Generate recommendations based on reconciliation
        if reconciliation_results["discrepancies"]:
            reconciliation_results["recommendations"].append(
                "Portfolio discrepancies detected. Consider refreshing account data."
            )
            
        # Check for rebalancing needs
        try:
            current_allocation = analytics.get_asset_allocation(user_id)
            if current_allocation:
                # Simple rebalancing check (this could be more sophisticated)
                max_weight = max(current_allocation.values()) if current_allocation else 0
                if max_weight > 0.4:  # 40% concentration threshold
                    reconciliation_results["recommendations"].append(
                        f"High concentration detected ({max_weight:.1%}). Consider rebalancing."
                    )
        except Exception as e:
            logger.warning(f"Could not check allocation for user {user_id}: {e}")
            
        logger.info(f"Portfolio reconciliation completed for user {user_id}")
        return reconciliation_results
        
    except Exception as e:
        logger.error(f"Portfolio reconciliation failed for user {user_id}: {e}")
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (2 ** self.request.retries))
        return {"error": str(e)}
    finally:
        db.close()

@celery_app.task
def reconcile_all_portfolios() -> Dict[str, Any]:
    """Reconcile portfolios for all users"""
    logger.info("Starting portfolio reconciliation for all users")
    
    db = SessionLocal()
    try:
        # Get all users with accounts
        users_with_accounts = db.query(User).join(Account).distinct().all()
        
        results = {
            "total_users": len(users_with_accounts),
            "successful_reconciliations": 0,
            "failed_reconciliations": 0,
            "total_discrepancies": 0,
            "errors": []
        }
        
        for user in users_with_accounts:
            try:
                # Queue individual portfolio reconciliation
                reconcile_result = reconcile_portfolio.delay(user.id)
                results["successful_reconciliations"] += 1
                logger.info(f"Queued reconciliation for user {user.id}")
            except Exception as e:
                results["failed_reconciliations"] += 1
                error_msg = f"Failed to queue reconciliation for user {user.id}: {str(e)}"
                results["errors"].append(error_msg)
                logger.error(error_msg)
                
        logger.info(f"Reconciliation queued for {results['successful_reconciliations']} users")
        return results
        
    except Exception as e:
        logger.error(f"Failed to reconcile all portfolios: {e}")
        return {"error": str(e)}
    finally:
        db.close()

@celery_app.task
def send_daily_reports() -> Dict[str, Any]:
    """Send daily reports to all users"""
    logger.info("Starting daily report generation")
    
    db = SessionLocal()
    try:
        notification_service = NotificationService(db)
        
        # Process all notifications
        results = notification_service.process_all_notifications()
        
        logger.info(f"Daily reports completed: {results}")
        return results
        
    except Exception as e:
        logger.error(f"Failed to send daily reports: {e}")
        return {"error": str(e)}
    finally:
        db.close()

@celery_app.task(bind=True, max_retries=5)
def sync_market_data(self, symbols: List[str]) -> Dict[str, Any]:
    """Sync market data for specified symbols"""
    logger.info(f"Syncing market data for {len(symbols)} symbols")
    
    try:
        from .market_data import market_data_manager
        
        results = {
            "symbols_processed": 0,
            "symbols_failed": 0,
            "errors": []
        }
        
        for symbol in symbols:
            try:
                # Subscribe to symbol for updates
                market_data_manager.subscribe(symbol, lambda q: None)
                results["symbols_processed"] += 1
            except Exception as e:
                results["symbols_failed"] += 1
                error_msg = f"Failed to sync data for {symbol}: {str(e)}"
                results["errors"].append(error_msg)
                logger.error(error_msg)
                
        return results
        
    except Exception as e:
        logger.error(f"Market data sync failed: {e}")
        if self.request.retries < self.max_retries:
            raise self.retry(countdown=30 * (2 ** self.request.retries))
        return {"error": str(e)}

@celery_app.task
def cleanup_old_data() -> Dict[str, Any]:
    """Clean up old data and logs"""
    logger.info("Starting data cleanup")
    
    db = SessionLocal()
    try:
        results = {
            "transactions_cleaned": 0,
            "old_logs_cleaned": 0
        }
        
        # Clean up old transactions (older than 2 years)
        cutoff_date = datetime.utcnow() - timedelta(days=730)
        old_transactions = db.query(Transaction).filter(
            Transaction.date < cutoff_date
        ).count()
        
        if old_transactions > 10000:  # Only clean if there are many old records
            db.query(Transaction).filter(
                Transaction.date < cutoff_date
            ).limit(1000).delete()  # Delete in batches
            results["transactions_cleaned"] = 1000
            
        db.commit()
        
        logger.info(f"Data cleanup completed: {results}")
        return results
        
    except Exception as e:
        db.rollback()
        logger.error(f"Data cleanup failed: {e}")
        return {"error": str(e)}
    finally:
        db.close()

# Task monitoring and management functions
def get_task_status(task_id: str) -> Dict[str, Any]:
    """Get status of a specific task"""
    result = celery_app.AsyncResult(task_id)
    return {
        "task_id": task_id,
        "status": result.status,
        "result": result.result,
        "info": result.info
    }

def get_active_tasks() -> List[Dict[str, Any]]:
    """Get list of active tasks"""
    inspect = celery_app.control.inspect()
    active_tasks = inspect.active()
    
    if not active_tasks:
        return []
        
    tasks = []
    for worker, task_list in active_tasks.items():
        for task in task_list:
            tasks.append({
                "worker": worker,
                "task_id": task["id"],
                "task_name": task["name"],
                "args": task["args"],
                "kwargs": task["kwargs"]
            })
            
    return tasks

def cancel_task(task_id: str) -> bool:
    """Cancel a specific task"""
    try:
        celery_app.control.revoke(task_id, terminate=True)
        return True
    except Exception as e:
        logger.error(f"Failed to cancel task {task_id}: {e}")
        return False

# Queue specific user sync
def queue_user_sync(user_id: int) -> str:
    """Queue sync for a specific user"""
    result = sync_user_accounts.delay(user_id)
    return result.id

# Queue specific portfolio reconciliation
def queue_portfolio_reconciliation(user_id: int) -> str:
    """Queue portfolio reconciliation for a specific user"""
    result = reconcile_portfolio.delay(user_id)
    return result.id