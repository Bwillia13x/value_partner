from dotenv import load_dotenv

load_dotenv()

import uuid
from fastapi import FastAPI, HTTPException, status, Request
from pydantic import BaseModel
from .license import LicenseMiddleware
import os
from .plugins import PLUGINS
from .portfolio_routes import router as portfolio_router
from .webhooks import router as webhooks_router
from .strategy_routes import router as strategy_router
from .analytics_routes import router as analytics_router
from .optimizer_routes import router as optimizer_router
from .reporting_routes import router as reporting_router
from .notifications_routes import router as notifications_router
from .auth_routes import router as auth_router
from .order_routes import router as order_router
from .tax_routes import router as tax_router
from .market_data_routes import router as market_data_router
from .integrations.plaid_routes import router as plaid_router
# from app.task_routes import router as task_router # Removed for debugging
from .unified_account_routes import router as unified_account_router
from .monitoring_routes import router as monitoring_router
from .websocket_routes import router as websocket_router
from .beta_testing_routes import router as beta_router
from .database import init_db
from celery import current_app as current_celery_app
from pathlib import Path
import pandas as pd
import logging
from datetime import datetime
from .logging_config import setup_logging
from .performance_monitor import performance_monitor
from .csrf_protection import CSRFProtectionMiddleware
from .monitoring import start_monitoring, track_http_request, app_monitor
from .real_time_sync import start_real_time_sync

# Initialize structured logging
logger = setup_logging()

try:
    from .copilot import CopilotRetriever

    retriever = CopilotRetriever()
except Exception:
    retriever = None


class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    answers: list[str]

app = FastAPI(
    title="Value Investing AI API",
    version="0.1.0",
    description="REST endpoints for the institutional-grade value-investing platform.",
    on_startup=[],
    on_shutdown=[]
)

# Add request tracing and monitoring middleware
@app.middleware("http")
async def request_tracing_middleware(request: Request, call_next):
    """Add request tracing, correlation ID, and monitoring to all requests"""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    # Skip monitoring for monitoring endpoints to avoid circular metrics
    skip_monitoring = request.url.path.startswith("/monitoring/") or request.url.path == "/health"
    
    # Log request start
    logger.info(f"Request started: {request.method} {request.url.path}", extra={
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
        "client_ip": request.client.host if request.client else "unknown"
    })
    
    # Track request with monitoring system
    if not skip_monitoring:
        with track_http_request(request.url.path, request.method) as tracker:
            try:
                response = await call_next(request)
                response.headers["X-Request-ID"] = request_id
                
                # Set status code for tracking
                tracker.set_status_code(response.status_code)
                
                # Log successful response
                logger.info(f"Request completed: {response.status_code}", extra={
                    "request_id": request_id,
                    "status_code": response.status_code
                })
                
                return response
            except Exception as e:
                # Log error
                logger.error(f"Request failed: {str(e)}", extra={
                    "request_id": request_id,
                    "error": str(e)
                })
                raise
    else:
        # Skip monitoring for internal endpoints
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            
            # Log successful response
            logger.info(f"Request completed: {response.status_code}", extra={
                "request_id": request_id,
                "status_code": response.status_code
            })
            
            return response
        except Exception as e:
            # Log error
            logger.error(f"Request failed: {str(e)}", extra={
                "request_id": request_id,
                "error": str(e)
            })
            raise

# Add CORS middleware
from fastapi.middleware.cors import CORSMiddleware

# Get allowed origins from environment, default to localhost for development
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Initialize database
init_db()

# Initialize Celery
def create_celery():
    # Configure Celery
    celery = current_celery_app
    celery.config_from_object('app.tasks.config')
    
    # Auto-discover tasks
    celery.autodiscover_tasks(['app.tasks.reconciliation'])
    
    return celery

# Add startup event
@app.on_event("startup")
async def startup_event():
    """Initialize services on application startup"""
    # Start monitoring system
    start_monitoring()
    logger.info("Monitoring system started")
    
    # Start real-time sync manager
    start_real_time_sync()
    logger.info("Real-time sync manager started")
    
    # Ensure the Celery app is properly configured
    create_celery()
    logger.info("Application startup: Celery worker initialized")
    
    # Start market data manager
    try:
        from .market_data import market_data_manager
        market_data_manager.start()
        logger.info("Market data manager started successfully")
    except Exception as e:
        logger.error(f"Failed to start market data manager: {e}")
    
    # Create a test task to verify Celery is working
    try:
        from .tasks.reconciliation import reconcile_all_accounts
        result = reconcile_all_accounts.delay()
        logger.info(f"Test Celery task enqueued with ID: {result.id}")
    except Exception as e:
        logger.error(f"Error enqueueing test Celery task: {e}")

# Add health check endpoint with comprehensive service status
@app.get("/health", include_in_schema=False)
async def health_check():
    """Basic health check endpoint"""
    # Use the monitoring system for health check
    health_status = app_monitor.get_health_status()
    
    # Return appropriate HTTP status based on health
    if health_status["status"] == "unhealthy":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=health_status
        )
    elif health_status["status"] == "degraded":
        return {"status": "degraded", **health_status}
    else:
        return {"status": "healthy", **health_status}

@app.get("/health/detailed", include_in_schema=False)
async def detailed_health_check():
    """Comprehensive health check endpoint that verifies all services"""
    from .error_handling import error_handler
    from .database import get_db
    import time
    
    health_results = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "services": {},
        "error_metrics": {}
    }
    
    # Check database connectivity
    try:
        from sqlalchemy import text
        db = next(get_db())
        start_time = time.time()
        db.execute(text("SELECT 1")).fetchone()
        db_response_time = time.time() - start_time
        health_results["services"]["database"] = {
            "status": "healthy",
            "response_time_ms": round(db_response_time * 1000, 2)
        }
    except Exception as e:
        health_results["services"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_results["status"] = "degraded"
    
    # Check Celery worker status
    try:
        import redis
        # Check Redis connectivity first
        redis_client = redis.Redis.from_url(os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0"))
        redis_client.ping()
        
        celery = create_celery()
        inspect = celery.control.inspect()
        stats = inspect.stats()
        active_tasks = inspect.active()
        
        if stats:
            health_results["services"]["celery"] = {
                "status": "healthy",
                "workers": len(stats),
                "active_tasks": sum(len(tasks) for tasks in (active_tasks or {}).values())
            }
        else:
            health_results["services"]["celery"] = {
                "status": "degraded",
                "warning": "No workers available but broker is reachable"
            }
    except Exception as e:
        health_results["services"]["celery"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Check error handler statistics
    try:
        error_stats = error_handler.get_error_statistics()
        health_results["error_metrics"] = {
            "total_errors_24h": error_stats.get("recent_errors_24h", 0),
            "circuit_breakers_active": error_stats.get("circuit_breakers_active", [])
        }
    except Exception as e:
        health_results["error_metrics"] = {
            "error": f"Unable to retrieve error statistics: {str(e)}"
        }
    
    # Set overall status
    unhealthy_services = [name for name, service in health_results["services"].items() 
                         if service["status"] == "unhealthy"]
    
    if unhealthy_services:
        health_results["status"] = "unhealthy"
        if len(unhealthy_services) < len(health_results["services"]):
            health_results["status"] = "degraded"
    
    # Return appropriate HTTP status
    if health_results["status"] == "unhealthy":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=health_results
        )
    elif health_results["status"] == "degraded":
        raise HTTPException(
            status_code=status.HTTP_206_PARTIAL_CONTENT,
            detail=health_results
        )
    
    return health_results

@app.get("/admin/performance", include_in_schema=False)
async def performance_metrics():
    """Administrative endpoint for performance metrics"""
    return {
        "performance_stats": performance_monitor.get_all_stats(),
        "timestamp": datetime.utcnow().isoformat()
    }

# Attach security middleware
if not os.getenv("TESTING"):
    app.add_middleware(LicenseMiddleware)
    
# Add CSRF Protection (after CORS but before other middleware)
if not os.getenv("TESTING"):
    app.add_middleware(CSRFProtectionMiddleware)

# Include portfolio routes
app.include_router(portfolio_router)
app.include_router(webhooks_router)
app.include_router(strategy_router)
app.include_router(analytics_router)
app.include_router(optimizer_router)
app.include_router(reporting_router)
app.include_router(notifications_router)
app.include_router(auth_router)
app.include_router(order_router)
app.include_router(tax_router)
app.include_router(market_data_router)
app.include_router(plaid_router)
# app.include_router(task_router) # Removed for debugging
app.include_router(unified_account_router)
app.include_router(monitoring_router)
app.include_router(websocket_router)
app.include_router(beta_router)



@app.post("/copilot/query", response_model=QueryResponse, tags=["Copilot"])
async def copilot_query(req: QueryRequest):
    if retriever is None:
        raise HTTPException(status_code=503, detail="Copilot not available")
    answers = retriever.query(req.question)
    return QueryResponse(answers=answers)


# ----------------- Marketplace Plugin Endpoints -----------------


@app.get("/plugins", tags=["Marketplace"])
async def list_plugins():
    return {"available_plugins": list(PLUGINS.keys())}


class PluginRequest(BaseModel):
    plugin: str
    payload: dict


@app.post("/plugins/run", tags=["Marketplace"])
async def run_plugin(req: PluginRequest):
    if req.plugin not in PLUGINS:
        raise HTTPException(status_code=404, detail="Plugin not found")
    try:
        result = PLUGINS[req.plugin](req.payload)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ----------------- Data Endpoints -----------------

FACTORS_FILE = Path("data/samples/factors.parquet")
BACKTEST_FILE = Path("models/backtester/results/cumulative_returns.csv")

@app.get("/data/factors", tags=["Data"])
async def get_factors(limit: int = 200):
    """Return first `limit` rows of the factors dataset as JSON."""
    if not FACTORS_FILE.exists():
        raise HTTPException(status_code=404, detail="Factors file not found")
    df = pd.read_parquet(FACTORS_FILE).head(limit)
    return {"columns": df.columns.tolist(), "rows": df.astype(str).values.tolist()}


@app.get("/data/backtest", tags=["Data"])
async def get_backtest():
    """Return cumulative returns CSV as list of records for charting."""
    if not BACKTEST_FILE.exists():
        raise HTTPException(status_code=404, detail="Backtest results not found")
    df = pd.read_csv(BACKTEST_FILE, parse_dates=["date"])
    df["date"] = df["date"].dt.strftime("%Y-%m-%d")
    return df.to_dict(orient="records")