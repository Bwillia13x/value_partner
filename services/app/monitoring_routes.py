"""Monitoring and health check API endpoints"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from .monitoring import (
    metrics_collector, alert_manager, system_monitor, app_monitor,
    AlertSeverity, MetricType
)
from .auth import get_current_active_user
from .models import User

router = APIRouter(prefix="/monitoring", tags=["monitoring"])

@router.get("/health")
async def health_check():
    """Basic health check endpoint - no authentication required"""
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

@router.get("/health/detailed")
async def detailed_health_check(current_user: User = Depends(get_current_active_user)):
    """Detailed health check with authentication required"""
    health_status = app_monitor.get_health_status()
    
    # Add system metrics
    system_metrics = {
        "cpu_percent": metrics_collector.get_gauge("system.cpu.percent"),
        "memory_percent": metrics_collector.get_gauge("system.memory.percent"),
        "disk_percent": metrics_collector.get_gauge("system.disk.percent"),
        "memory_available": metrics_collector.get_gauge("system.memory.available"),
        "disk_free": metrics_collector.get_gauge("system.disk.free"),
    }
    
    # Add database metrics
    db_metrics = {
        "total_operations": metrics_collector.get_counter("db.operations.total"),
        "total_errors": metrics_collector.get_counter("db.operations.errors"),
        "operation_duration_stats": metrics_collector.get_histogram_stats("db.operation.duration")
    }
    
    # Add order metrics
    order_metrics = {
        "total_operations": metrics_collector.get_counter("orders.operations.total"),
        "operation_duration_stats": metrics_collector.get_histogram_stats("orders.operation.duration")
    }
    
    # Add Alpaca metrics
    alpaca_metrics = {
        "total_operations": metrics_collector.get_counter("alpaca.operations.total"),
        "total_errors": metrics_collector.get_counter("alpaca.operations.errors"),
        "operation_duration_stats": metrics_collector.get_histogram_stats("alpaca.operation.duration")
    }
    
    return {
        **health_status,
        "system_metrics": system_metrics,
        "database_metrics": db_metrics,
        "order_metrics": order_metrics,
        "alpaca_metrics": alpaca_metrics
    }

@router.get("/metrics")
async def get_metrics(
    since_hours: Optional[int] = Query(1, description="Get metrics from last N hours"),
    metric_name: Optional[str] = Query(None, description="Filter by metric name"),
    current_user: User = Depends(get_current_active_user)
):
    """Get application metrics"""
    since = datetime.utcnow() - timedelta(hours=since_hours) if since_hours else None
    metrics = metrics_collector.get_metrics(since)
    
    if metric_name:
        metrics = [m for m in metrics if m.name == metric_name]
    
    return {
        "metrics": [
            {
                "name": metric.name,
                "value": metric.value,
                "type": metric.type.value,
                "timestamp": metric.timestamp.isoformat(),
                "tags": metric.tags
            }
            for metric in metrics
        ],
        "count": len(metrics)
    }

@router.get("/metrics/summary")
async def get_metrics_summary(current_user: User = Depends(get_current_active_user)):
    """Get summary of all metrics"""
    
    # HTTP metrics
    http_summary = {
        "total_requests": metrics_collector.get_counter("http.requests.total"),
        "total_errors": metrics_collector.get_counter("http.requests.errors"),
        "response_time_stats": metrics_collector.get_histogram_stats("http.request.duration")
    }
    
    # System metrics
    system_summary = {
        "cpu_percent": metrics_collector.get_gauge("system.cpu.percent"),
        "memory_percent": metrics_collector.get_gauge("system.memory.percent"),
        "disk_percent": metrics_collector.get_gauge("system.disk.percent"),
        "process_memory_rss": metrics_collector.get_gauge("process.memory.rss"),
        "process_cpu_percent": metrics_collector.get_gauge("process.cpu.percent"),
        "process_num_threads": metrics_collector.get_gauge("process.num_threads")
    }
    
    # Database metrics
    db_summary = {
        "total_operations": metrics_collector.get_counter("db.operations.total"),
        "total_errors": metrics_collector.get_counter("db.operations.errors"),
        "operation_duration_stats": metrics_collector.get_histogram_stats("db.operation.duration")
    }
    
    # Order metrics
    order_summary = {
        "total_operations": metrics_collector.get_counter("orders.operations.total"),
        "operation_duration_stats": metrics_collector.get_histogram_stats("orders.operation.duration")
    }
    
    # Alpaca metrics
    alpaca_summary = {
        "total_operations": metrics_collector.get_counter("alpaca.operations.total"),
        "total_errors": metrics_collector.get_counter("alpaca.operations.errors"),
        "operation_duration_stats": metrics_collector.get_histogram_stats("alpaca.operation.duration")
    }
    
    return {
        "http": http_summary,
        "system": system_summary,
        "database": db_summary,
        "orders": order_summary,
        "alpaca": alpaca_summary
    }

@router.get("/alerts")
async def get_alerts(
    active_only: bool = Query(False, description="Get only active alerts"),
    severity: Optional[AlertSeverity] = Query(None, description="Filter by severity"),
    since_hours: Optional[int] = Query(24, description="Get alerts from last N hours"),
    current_user: User = Depends(get_current_active_user)
):
    """Get application alerts"""
    
    if active_only:
        alerts = alert_manager.get_active_alerts()
    else:
        since = datetime.utcnow() - timedelta(hours=since_hours) if since_hours else None
        alerts = alert_manager.get_alerts(since=since, severity=severity)
    
    return {
        "alerts": [
            {
                "name": alert.name,
                "severity": alert.severity.value,
                "message": alert.message,
                "timestamp": alert.timestamp.isoformat(),
                "resolved": alert.resolved,
                "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
                "tags": alert.tags
            }
            for alert in alerts
        ],
        "count": len(alerts)
    }

@router.post("/alerts/{alert_name}/resolve")
async def resolve_alert(
    alert_name: str,
    current_user: User = Depends(get_current_active_user)
):
    """Manually resolve an alert"""
    success = alert_manager.resolve_alert(alert_name)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert '{alert_name}' not found or already resolved"
        )
    
    return {"message": f"Alert '{alert_name}' resolved successfully"}

@router.post("/alerts/test")
async def trigger_test_alert(
    severity: AlertSeverity = AlertSeverity.LOW,
    current_user: User = Depends(get_current_active_user)
):
    """Trigger a test alert for testing notification systems"""
    alert_name = f"test_alert_{int(datetime.utcnow().timestamp())}"
    message = f"This is a test alert with {severity.value} severity"
    
    success = alert_manager.trigger_alert(alert_name, severity, message, {"test": "true"})
    
    if success:
        return {"message": f"Test alert '{alert_name}' triggered successfully"}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to trigger test alert"
        )

@router.get("/performance")
async def get_performance_metrics(
    hours: int = Query(24, description="Performance metrics for last N hours"),
    current_user: User = Depends(get_current_active_user)
):
    """Get performance metrics and statistics"""
    
    # Calculate error rates
    total_requests = metrics_collector.get_counter("http.requests.total")
    total_errors = metrics_collector.get_counter("http.requests.errors")
    http_error_rate = (total_errors / total_requests) if total_requests > 0 else 0
    
    # Database error rate
    total_db_ops = metrics_collector.get_counter("db.operations.total")
    total_db_errors = metrics_collector.get_counter("db.operations.errors")
    db_error_rate = (total_db_errors / total_db_ops) if total_db_ops > 0 else 0
    
    # Alpaca error rate
    total_alpaca_ops = metrics_collector.get_counter("alpaca.operations.total")
    total_alpaca_errors = metrics_collector.get_counter("alpaca.operations.errors")
    alpaca_error_rate = (total_alpaca_errors / total_alpaca_ops) if total_alpaca_ops > 0 else 0
    
    # Response time percentiles
    http_response_stats = metrics_collector.get_histogram_stats("http.request.duration")
    db_response_stats = metrics_collector.get_histogram_stats("db.operation.duration")
    alpaca_response_stats = metrics_collector.get_histogram_stats("alpaca.operation.duration")
    
    return {
        "period_hours": hours,
        "http": {
            "total_requests": total_requests,
            "total_errors": total_errors,
            "error_rate": http_error_rate,
            "response_time_stats": http_response_stats
        },
        "database": {
            "total_operations": total_db_ops,
            "total_errors": total_db_errors,
            "error_rate": db_error_rate,
            "response_time_stats": db_response_stats
        },
        "alpaca": {
            "total_operations": total_alpaca_ops,
            "total_errors": total_alpaca_errors,
            "error_rate": alpaca_error_rate,
            "response_time_stats": alpaca_response_stats
        }
    }

@router.get("/system")
async def get_system_info(current_user: User = Depends(get_current_active_user)):
    """Get system information and resource usage"""
    import platform
    import sys
    
    return {
        "system": {
            "platform": platform.platform(),
            "python_version": sys.version,
            "architecture": platform.architecture(),
            "processor": platform.processor(),
            "hostname": platform.node()
        },
        "resources": {
            "cpu_percent": metrics_collector.get_gauge("system.cpu.percent"),
            "memory_percent": metrics_collector.get_gauge("system.memory.percent"),
            "memory_available": metrics_collector.get_gauge("system.memory.available"),
            "memory_used": metrics_collector.get_gauge("system.memory.used"),
            "disk_percent": metrics_collector.get_gauge("system.disk.percent"),
            "disk_free": metrics_collector.get_gauge("system.disk.free"),
            "disk_used": metrics_collector.get_gauge("system.disk.used"),
            "network_bytes_sent": metrics_collector.get_gauge("system.network.bytes_sent"),
            "network_bytes_recv": metrics_collector.get_gauge("system.network.bytes_recv")
        },
        "process": {
            "memory_rss": metrics_collector.get_gauge("process.memory.rss"),
            "memory_vms": metrics_collector.get_gauge("process.memory.vms"),
            "cpu_percent": metrics_collector.get_gauge("process.cpu.percent"),
            "num_threads": metrics_collector.get_gauge("process.num_threads")
        }
    }

@router.get("/uptime")
async def get_uptime():
    """Get application uptime - no authentication required"""
    uptime_seconds = (datetime.utcnow() - app_monitor.start_time).total_seconds()
    
    days = int(uptime_seconds // 86400)
    hours = int((uptime_seconds % 86400) // 3600)
    minutes = int((uptime_seconds % 3600) // 60)
    seconds = int(uptime_seconds % 60)
    
    return {
        "uptime_seconds": uptime_seconds,
        "uptime_formatted": f"{days}d {hours}h {minutes}m {seconds}s",
        "start_time": app_monitor.start_time.isoformat()
    }