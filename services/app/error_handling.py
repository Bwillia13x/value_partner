"""Comprehensive error handling and retry mechanisms"""
import logging
import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, Callable, Any, Type, Tuple
from dataclasses import dataclass
from enum import Enum
import traceback
from functools import wraps
from sqlalchemy.exc import SQLAlchemyError
import requests
from requests.exceptions import RequestException, ConnectionError, Timeout

from .database import get_db

logger = logging.getLogger(__name__)

class ErrorSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(Enum):
    NETWORK = "network"
    DATABASE = "database"
    AUTHENTICATION = "authentication"
    VALIDATION = "validation"
    BUSINESS_LOGIC = "business_logic"
    EXTERNAL_API = "external_api"
    SYSTEM = "system"

@dataclass
class ErrorContext:
    """Error context information"""
    user_id: Optional[int] = None
    account_id: Optional[int] = None
    function_name: Optional[str] = None
    request_id: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None

@dataclass
class ErrorRecord:
    """Error record for tracking and analysis"""
    error_id: str
    timestamp: datetime
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    stack_trace: str
    context: ErrorContext
    retry_count: int = 0
    resolved: bool = False
    resolution_notes: Optional[str] = None

class RetryConfig:
    """Configuration for retry mechanisms"""
    
    def __init__(self, 
                 max_attempts: int = 3,
                 initial_delay: float = 1.0,
                 backoff_factor: float = 2.0,
                 max_delay: float = 60.0,
                 jitter: bool = True):
        self.max_attempts = max_attempts
        self.initial_delay = initial_delay
        self.backoff_factor = backoff_factor
        self.max_delay = max_delay
        self.jitter = jitter

class ErrorHandler:
    """Centralized error handling system"""
    
    def __init__(self):
        self.error_records: Dict[str, ErrorRecord] = {}
        self.error_counts: Dict[str, int] = {}  # Count by category
        self.circuit_breakers: Dict[str, Dict[str, Any]] = {}
        
    def record_error(self, 
                    error: Exception, 
                    category: ErrorCategory,
                    severity: ErrorSeverity,
                    context: Optional[ErrorContext] = None) -> str:
        """Record an error for tracking and analysis"""
        
        error_id = f"{category.value}_{int(time.time() * 1000)}"
        
        error_record = ErrorRecord(
            error_id=error_id,
            timestamp=datetime.utcnow(),
            category=category,
            severity=severity,
            message=str(error),
            stack_trace=traceback.format_exc(),
            context=context or ErrorContext()
        )
        
        self.error_records[error_id] = error_record
        
        # Update error counts
        self.error_counts[category.value] = self.error_counts.get(category.value, 0) + 1
        
        # Log the error
        log_level = logging.ERROR if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL] else logging.WARNING
        logger.log(log_level, f"Error recorded [{error_id}] {category.value}: {str(error)}")
        
        # Check for circuit breaker conditions
        self._check_circuit_breaker(category, error)
        
        return error_id
        
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics and trends"""
        
        total_errors = len(self.error_records)
        recent_errors = len([
            err for err in self.error_records.values()
            if err.timestamp > datetime.utcnow() - timedelta(hours=24)
        ])
        
        severity_counts = {}
        for severity in ErrorSeverity:
            severity_counts[severity.value] = len([
                err for err in self.error_records.values()
                if err.severity == severity
            ])
            
        return {
            "total_errors": total_errors,
            "recent_errors_24h": recent_errors,
            "errors_by_category": self.error_counts,
            "errors_by_severity": severity_counts,
            "circuit_breakers_active": len([
                cb for cb in self.circuit_breakers.values()
                if cb.get("open", False)
            ])
        }
    
    def get_circuit_breaker_status(self):
        """Get status of all circuit breakers"""
        return {
            category: {
                "open": cb.get("open", False),
                "failure_count": cb.get("failure_count", 0),
                "last_failure": cb.get("last_failure").isoformat() if cb.get("last_failure") else None
            }
            for category, cb in self.circuit_breakers.items()
        }
    
    def check_health(self):
        """Check overall health of error handling system"""
        stats = self.get_error_statistics()
        open_circuits = [cat for cat, cb in self.circuit_breakers.items() if cb.get("open", False)]
        
        return {
            "status": "degraded" if open_circuits else "healthy",
            "open_circuit_breakers": open_circuits,
            "recent_error_rate": stats["recent_errors_24h"] / 1440,  # errors per minute
            "total_errors": stats["total_errors"]
        }
        
    def _check_circuit_breaker(self, category: ErrorCategory, error: Exception):
        """Check if circuit breaker should be activated"""
        
        key = category.value
        
        if key not in self.circuit_breakers:
            self.circuit_breakers[key] = {
                "failure_count": 0,
                "last_failure": None,
                "open": False,
                "half_open_attempts": 0
            }
            
        cb = self.circuit_breakers[key]
        cb["failure_count"] += 1
        cb["last_failure"] = datetime.utcnow()
        
        # Open circuit breaker if too many failures
        if cb["failure_count"] >= 5 and not cb["open"]:
            cb["open"] = True
            logger.warning(f"Circuit breaker opened for {category.value}")
            
    def is_circuit_breaker_open(self, category: ErrorCategory) -> bool:
        """Check if circuit breaker is open for a category"""
        
        key = category.value
        if key not in self.circuit_breakers:
            return False
            
        cb = self.circuit_breakers[key]
        
        if not cb["open"]:
            return False
            
        # Check if enough time has passed to try half-open
        if cb["last_failure"] and (datetime.utcnow() - cb["last_failure"]) > timedelta(minutes=5):
            cb["open"] = False
            cb["half_open_attempts"] = 0
            logger.info(f"Circuit breaker reset for {category.value}")
            return False
            
        return True

# Global error handler instance
error_handler = ErrorHandler()

def retry_with_backoff(config: Optional[RetryConfig] = None,
                      exceptions: Tuple[Type[Exception], ...] = (Exception,),
                      category: ErrorCategory = ErrorCategory.SYSTEM):
    """Decorator for implementing retry logic with exponential backoff"""
    
    if config is None:
        config = RetryConfig()
        
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(config.max_attempts):
                try:
                    # Check circuit breaker
                    if error_handler.is_circuit_breaker_open(category):
                        raise Exception(f"Circuit breaker open for {category.value}")
                        
                    return func(*args, **kwargs)
                    
                except exceptions as e:
                    last_exception = e
                    
                    # Record the error
                    context = ErrorContext(
                        function_name=func.__name__,
                        additional_data={"attempt": attempt + 1, "max_attempts": config.max_attempts}
                    )
                    
                    severity = ErrorSeverity.MEDIUM if attempt < config.max_attempts - 1 else ErrorSeverity.HIGH
                    error_handler.record_error(e, category, severity, context)
                    
                    # Don't retry on last attempt
                    if attempt == config.max_attempts - 1:
                        break
                        
                    # Calculate delay
                    delay = min(
                        config.initial_delay * (config.backoff_factor ** attempt),
                        config.max_delay
                    )
                    
                    # Add jitter if enabled
                    if config.jitter:
                        import random
                        delay *= (0.5 + random.random() * 0.5)
                        
                    logger.info(f"Retrying {func.__name__} in {delay:.2f}s (attempt {attempt + 1}/{config.max_attempts})")
                    time.sleep(delay)
                    
            # All retries exhausted
            raise last_exception
            
        return wrapper
    return decorator

async def async_retry_with_backoff(config: Optional[RetryConfig] = None,
                                  exceptions: Tuple[Type[Exception], ...] = (Exception,),
                                  category: ErrorCategory = ErrorCategory.SYSTEM):
    """Async version of retry decorator"""
    
    if config is None:
        config = RetryConfig()
        
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(config.max_attempts):
                try:
                    # Check circuit breaker
                    if error_handler.is_circuit_breaker_open(category):
                        raise Exception(f"Circuit breaker open for {category.value}")
                        
                    return await func(*args, **kwargs)
                    
                except exceptions as e:
                    last_exception = e
                    
                    # Record the error
                    context = ErrorContext(
                        function_name=func.__name__,
                        additional_data={"attempt": attempt + 1, "max_attempts": config.max_attempts}
                    )
                    
                    severity = ErrorSeverity.MEDIUM if attempt < config.max_attempts - 1 else ErrorSeverity.HIGH
                    error_handler.record_error(e, category, severity, context)
                    
                    # Don't retry on last attempt
                    if attempt == config.max_attempts - 1:
                        break
                        
                    # Calculate delay
                    delay = min(
                        config.initial_delay * (config.backoff_factor ** attempt),
                        config.max_delay
                    )
                    
                    # Add jitter if enabled
                    if config.jitter:
                        import random
                        delay *= (0.5 + random.random() * 0.5)
                        
                    logger.info(f"Retrying {func.__name__} in {delay:.2f}s (attempt {attempt + 1}/{config.max_attempts})")
                    await asyncio.sleep(delay)
                    
            # All retries exhausted
            raise last_exception
            
        return wrapper
    return decorator

# Specific retry configurations for different scenarios
API_RETRY_CONFIG = RetryConfig(max_attempts=3, initial_delay=1.0, backoff_factor=2.0)
DATABASE_RETRY_CONFIG = RetryConfig(max_attempts=5, initial_delay=0.5, backoff_factor=1.5)
NETWORK_RETRY_CONFIG = RetryConfig(max_attempts=4, initial_delay=2.0, backoff_factor=2.0)

# Decorators for common scenarios
def retry_api_call(func):
    """Retry decorator for API calls"""
    return retry_with_backoff(
        config=API_RETRY_CONFIG,
        exceptions=(RequestException, ConnectionError, Timeout),
        category=ErrorCategory.EXTERNAL_API
    )(func)

def retry_database_operation(func):
    """Retry decorator for database operations"""
    return retry_with_backoff(
        config=DATABASE_RETRY_CONFIG,
        exceptions=(SQLAlchemyError,),
        category=ErrorCategory.DATABASE
    )(func)

def retry_network_operation(func):
    """Retry decorator for network operations"""
    return retry_with_backoff(
        config=NETWORK_RETRY_CONFIG,
        exceptions=(ConnectionError, Timeout, OSError),
        category=ErrorCategory.NETWORK
    )(func)

class HealthChecker:
    """System health monitoring"""
    
    def __init__(self):
        self.health_checks: Dict[str, Callable] = {}
        self.last_check_results: Dict[str, Dict[str, Any]] = {}
        
    def register_health_check(self, name: str, check_func: Callable):
        """Register a health check function"""
        self.health_checks[name] = check_func
        
    async def run_health_checks(self) -> Dict[str, Any]:
        """Run all registered health checks"""
        
        results = {
            "overall_status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {}
        }
        
        for name, check_func in self.health_checks.items():
            try:
                start_time = time.time()
                check_result = await check_func() if asyncio.iscoroutinefunction(check_func) else check_func()
                duration = time.time() - start_time
                
                results["checks"][name] = {
                    "status": "healthy",
                    "duration_ms": round(duration * 1000, 2),
                    "details": check_result
                }
                
            except Exception as e:
                results["checks"][name] = {
                    "status": "unhealthy",
                    "error": str(e),
                    "details": None
                }
                results["overall_status"] = "unhealthy"
                
                # Record health check failure
                context = ErrorContext(function_name=f"health_check_{name}")
                error_handler.record_error(e, ErrorCategory.SYSTEM, ErrorSeverity.MEDIUM, context)
                
        self.last_check_results = results
        return results
        
    def get_last_results(self) -> Dict[str, Any]:
        """Get last health check results"""
        return self.last_check_results

# Global health checker instance
health_checker = HealthChecker()

# Register default health checks
def check_database_connection():
    """Check database connectivity"""
    try:
        db = next(get_db())
        db.execute("SELECT 1")
        db.close()
        return {"status": "connected"}
    except Exception as e:
        raise Exception(f"Database connection failed: {str(e)}")

def check_error_handler_status():
    """Check error handler status"""
    stats = error_handler.get_error_statistics()
    
    if stats["recent_errors_24h"] > 100:
        raise Exception(f"High error rate: {stats['recent_errors_24h']} errors in 24h")
        
    return {
        "total_errors": stats["total_errors"],
        "recent_errors": stats["recent_errors_24h"],
        "status": "normal"
    }

# Register default health checks
health_checker.register_health_check("database", check_database_connection)
health_checker.register_health_check("error_handler", check_error_handler_status)

# Utility functions for common error scenarios
def handle_api_error(func):
    """Handle common API errors"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except requests.exceptions.Timeout as e:
            context = ErrorContext(function_name=func.__name__)
            error_handler.record_error(e, ErrorCategory.EXTERNAL_API, ErrorSeverity.MEDIUM, context)
            raise Exception("API request timed out. Please try again later.")
        except requests.exceptions.ConnectionError as e:
            context = ErrorContext(function_name=func.__name__)
            error_handler.record_error(e, ErrorCategory.NETWORK, ErrorSeverity.HIGH, context)
            raise Exception("Unable to connect to external service. Please check your connection.")
        except requests.exceptions.HTTPError as e:
            context = ErrorContext(function_name=func.__name__)
            severity = ErrorSeverity.HIGH if e.response.status_code >= 500 else ErrorSeverity.MEDIUM
            error_handler.record_error(e, ErrorCategory.EXTERNAL_API, severity, context)
            raise Exception(f"API request failed with status {e.response.status_code}")
    return wrapper

def safe_database_operation(func):
    """Safely execute database operations with proper error handling"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        db = None
        try:
            return func(*args, **kwargs)
        except SQLAlchemyError as e:
            if 'db' in locals() and db:
                db.rollback()
            context = ErrorContext(function_name=func.__name__)
            error_handler.record_error(e, ErrorCategory.DATABASE, ErrorSeverity.HIGH, context)
            raise Exception("Database operation failed. Please try again.")
        except Exception as e:
            if 'db' in locals() and db:
                db.rollback()
            context = ErrorContext(function_name=func.__name__)
            error_handler.record_error(e, ErrorCategory.BUSINESS_LOGIC, ErrorSeverity.MEDIUM, context)
            raise
        finally:
            if 'db' in locals() and db:
                db.close()
    return wrapper