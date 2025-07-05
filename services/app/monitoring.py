"""Production monitoring and alerting system"""
import os
import time
import logging
import psutil
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
from threading import Lock
import asyncio
from enum import Enum

logger = logging.getLogger(__name__)

class AlertSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class MetricType(Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"

@dataclass
class Metric:
    name: str
    value: float
    type: MetricType
    timestamp: datetime
    tags: Dict[str, str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = {}

@dataclass
class Alert:
    name: str
    severity: AlertSeverity
    message: str
    timestamp: datetime
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    tags: Dict[str, str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = {}

class MetricsCollector:
    """Collects and stores application metrics"""
    
    def __init__(self, max_metrics: int = 10000):
        self.metrics = deque(maxlen=max_metrics)
        self.counters = defaultdict(float)
        self.gauges = {}
        self.histograms = defaultdict(list)
        self.timers = defaultdict(list)
        self.lock = Lock()
    
    def increment(self, name: str, value: float = 1.0, tags: Dict[str, str] = None):
        """Increment a counter metric"""
        with self.lock:
            key = self._make_key(name, tags)
            self.counters[key] += value
            self._add_metric(name, self.counters[key], MetricType.COUNTER, tags)
    
    def gauge(self, name: str, value: float, tags: Dict[str, str] = None):
        """Set a gauge metric"""
        with self.lock:
            key = self._make_key(name, tags)
            self.gauges[key] = value
            self._add_metric(name, value, MetricType.GAUGE, tags)
    
    def histogram(self, name: str, value: float, tags: Dict[str, str] = None):
        """Add a value to a histogram"""
        with self.lock:
            key = self._make_key(name, tags)
            self.histograms[key].append(value)
            # Keep only last 1000 values for memory efficiency
            if len(self.histograms[key]) > 1000:
                self.histograms[key] = self.histograms[key][-1000:]
            self._add_metric(name, value, MetricType.HISTOGRAM, tags)
    
    def timer(self, name: str, value: float, tags: Dict[str, str] = None):
        """Add a timing value"""
        with self.lock:
            key = self._make_key(name, tags)
            self.timers[key].append(value)
            # Keep only last 1000 values for memory efficiency
            if len(self.timers[key]) > 1000:
                self.timers[key] = self.timers[key][-1000:]
            self._add_metric(name, value, MetricType.TIMER, tags)
    
    def get_metrics(self, since: Optional[datetime] = None) -> List[Metric]:
        """Get metrics since a specific time"""
        with self.lock:
            if since is None:
                return list(self.metrics)
            return [m for m in self.metrics if m.timestamp >= since]
    
    def get_counter(self, name: str, tags: Dict[str, str] = None) -> float:
        """Get current counter value"""
        key = self._make_key(name, tags)
        return self.counters.get(key, 0.0)
    
    def get_gauge(self, name: str, tags: Dict[str, str] = None) -> Optional[float]:
        """Get current gauge value"""
        key = self._make_key(name, tags)
        return self.gauges.get(key)
    
    def get_histogram_stats(self, name: str, tags: Dict[str, str] = None) -> Dict[str, float]:
        """Get histogram statistics"""
        key = self._make_key(name, tags)
        values = self.histograms.get(key, [])
        if not values:
            return {}
        
        values_sorted = sorted(values)
        n = len(values)
        
        return {
            "count": n,
            "min": min(values),
            "max": max(values),
            "mean": sum(values) / n,
            "p50": values_sorted[n // 2],
            "p95": values_sorted[int(n * 0.95)] if n > 20 else values_sorted[-1],
            "p99": values_sorted[int(n * 0.99)] if n > 100 else values_sorted[-1]
        }
    
    def _make_key(self, name: str, tags: Dict[str, str] = None) -> str:
        """Create a unique key for the metric"""
        if tags:
            tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
            return f"{name}[{tag_str}]"
        return name
    
    def _add_metric(self, name: str, value: float, metric_type: MetricType, tags: Dict[str, str] = None):
        """Add a metric to the collection"""
        metric = Metric(
            name=name,
            value=value,
            type=metric_type,
            timestamp=datetime.utcnow(),
            tags=tags or {}
        )
        self.metrics.append(metric)

class AlertManager:
    """Manages application alerts and notifications"""
    
    def __init__(self, max_alerts: int = 1000):
        self.alerts = deque(maxlen=max_alerts)
        self.active_alerts = {}  # name -> Alert
        self.lock = Lock()
        self.notification_handlers = []
    
    def add_notification_handler(self, handler):
        """Add a notification handler function"""
        self.notification_handlers.append(handler)
    
    def trigger_alert(self, name: str, severity: AlertSeverity, message: str, 
                     tags: Dict[str, str] = None) -> bool:
        """Trigger a new alert"""
        with self.lock:
            # Check if alert is already active
            if name in self.active_alerts and not self.active_alerts[name].resolved:
                logger.debug(f"Alert {name} is already active")
                return False
            
            alert = Alert(
                name=name,
                severity=severity,
                message=message,
                timestamp=datetime.utcnow(),
                tags=tags or {}
            )
            
            self.alerts.append(alert)
            self.active_alerts[name] = alert
            
            logger.warning(f"Alert triggered: {name} ({severity.value}) - {message}")
            
            # Send notifications
            self._send_notifications(alert)
            
            return True
    
    def resolve_alert(self, name: str) -> bool:
        """Resolve an active alert"""
        with self.lock:
            if name not in self.active_alerts:
                return False
            
            alert = self.active_alerts[name]
            if alert.resolved:
                return False
            
            alert.resolved = True
            alert.resolved_at = datetime.utcnow()
            
            logger.info(f"Alert resolved: {name}")
            return True
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts"""
        with self.lock:
            return [alert for alert in self.active_alerts.values() if not alert.resolved]
    
    def get_alerts(self, since: Optional[datetime] = None, severity: Optional[AlertSeverity] = None) -> List[Alert]:
        """Get alerts with optional filtering"""
        with self.lock:
            alerts = list(self.alerts)
            
            if since:
                alerts = [a for a in alerts if a.timestamp >= since]
            
            if severity:
                alerts = [a for a in alerts if a.severity == severity]
            
            return alerts
    
    def _send_notifications(self, alert: Alert):
        """Send notifications for an alert"""
        for handler in self.notification_handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Error in notification handler: {e}")

class SystemMonitor:
    """Monitors system resources and health"""
    
    def __init__(self, metrics_collector: MetricsCollector, alert_manager: AlertManager):
        self.metrics = metrics_collector
        self.alerts = alert_manager
        self.thresholds = {
            "cpu_percent": 80.0,
            "memory_percent": 85.0,
            "disk_percent": 90.0,
            "response_time_p95": 5.0,  # seconds
            "error_rate": 0.05  # 5%
        }
    
    def collect_system_metrics(self):
        """Collect system resource metrics"""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            self.metrics.gauge("system.cpu.percent", cpu_percent)
            
            # Memory usage
            memory = psutil.virtual_memory()
            self.metrics.gauge("system.memory.percent", memory.percent)
            self.metrics.gauge("system.memory.available", memory.available)
            self.metrics.gauge("system.memory.used", memory.used)
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            self.metrics.gauge("system.disk.percent", disk_percent)
            self.metrics.gauge("system.disk.free", disk.free)
            self.metrics.gauge("system.disk.used", disk.used)
            
            # Network I/O
            network = psutil.net_io_counters()
            self.metrics.gauge("system.network.bytes_sent", network.bytes_sent)
            self.metrics.gauge("system.network.bytes_recv", network.bytes_recv)
            
            # Process information
            process = psutil.Process()
            self.metrics.gauge("process.memory.rss", process.memory_info().rss)
            self.metrics.gauge("process.memory.vms", process.memory_info().vms)
            self.metrics.gauge("process.cpu.percent", process.cpu_percent())
            self.metrics.gauge("process.num_threads", process.num_threads())
            
            # Check thresholds and trigger alerts
            self._check_system_alerts(cpu_percent, memory.percent, disk_percent)
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
    
    def _check_system_alerts(self, cpu_percent: float, memory_percent: float, disk_percent: float):
        """Check system metrics against thresholds and trigger alerts"""
        # CPU alert
        if cpu_percent > self.thresholds["cpu_percent"]:
            self.alerts.trigger_alert(
                "high_cpu_usage",
                AlertSeverity.HIGH,
                f"CPU usage is {cpu_percent:.1f}% (threshold: {self.thresholds['cpu_percent']}%)"
            )
        else:
            self.alerts.resolve_alert("high_cpu_usage")
        
        # Memory alert
        if memory_percent > self.thresholds["memory_percent"]:
            self.alerts.trigger_alert(
                "high_memory_usage",
                AlertSeverity.HIGH,
                f"Memory usage is {memory_percent:.1f}% (threshold: {self.thresholds['memory_percent']}%)"
            )
        else:
            self.alerts.resolve_alert("high_memory_usage")
        
        # Disk alert
        if disk_percent > self.thresholds["disk_percent"]:
            self.alerts.trigger_alert(
                "high_disk_usage",
                AlertSeverity.CRITICAL,
                f"Disk usage is {disk_percent:.1f}% (threshold: {self.thresholds['disk_percent']}%)"
            )
        else:
            self.alerts.resolve_alert("high_disk_usage")

class ApplicationMonitor:
    """Monitors application-specific metrics and health"""
    
    def __init__(self, metrics_collector: MetricsCollector, alert_manager: AlertManager):
        self.metrics = metrics_collector
        self.alerts = alert_manager
        self.start_time = datetime.utcnow()
    
    def track_request(self, endpoint: str, method: str, status_code: int, duration: float):
        """Track HTTP request metrics"""
        tags = {
            "endpoint": endpoint,
            "method": method,
            "status_code": str(status_code)
        }
        
        # Increment request counter
        self.metrics.increment("http.requests.total", tags=tags)
        
        # Track response time
        self.metrics.timer("http.request.duration", duration, tags=tags)
        
        # Track errors
        if status_code >= 400:
            self.metrics.increment("http.requests.errors", tags=tags)
    
    def track_database_operation(self, operation: str, table: str, duration: float, success: bool):
        """Track database operation metrics"""
        tags = {
            "operation": operation,
            "table": table,
            "success": str(success)
        }
        
        self.metrics.increment("db.operations.total", tags=tags)
        self.metrics.timer("db.operation.duration", duration, tags=tags)
        
        if not success:
            self.metrics.increment("db.operations.errors", tags=tags)
    
    def track_order_operation(self, operation: str, status: str, duration: float = None):
        """Track order management operations"""
        tags = {
            "operation": operation,
            "status": status
        }
        
        self.metrics.increment("orders.operations.total", tags=tags)
        
        if duration is not None:
            self.metrics.timer("orders.operation.duration", duration, tags=tags)
    
    def track_alpaca_operation(self, operation: str, success: bool, duration: float = None):
        """Track Alpaca API operations"""
        tags = {
            "operation": operation,
            "success": str(success)
        }
        
        self.metrics.increment("alpaca.operations.total", tags=tags)
        
        if duration is not None:
            self.metrics.timer("alpaca.operation.duration", duration, tags=tags)
        
        if not success:
            self.metrics.increment("alpaca.operations.errors", tags=tags)
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall application health status"""
        uptime = datetime.utcnow() - self.start_time
        
        # Calculate error rates
        total_requests = self.metrics.get_counter("http.requests.total")
        total_errors = self.metrics.get_counter("http.requests.errors")
        error_rate = (total_errors / total_requests) if total_requests > 0 else 0
        
        # Get response time statistics
        response_time_stats = self.metrics.get_histogram_stats("http.request.duration")
        
        # Get active alerts
        active_alerts = self.alerts.get_active_alerts()
        
        # Determine overall health
        health_status = "healthy"
        if len(active_alerts) > 0:
            if any(alert.severity in [AlertSeverity.HIGH, AlertSeverity.CRITICAL] for alert in active_alerts):
                health_status = "unhealthy"
            else:
                health_status = "degraded"
        
        return {
            "status": health_status,
            "uptime_seconds": uptime.total_seconds(),
            "error_rate": error_rate,
            "total_requests": total_requests,
            "total_errors": total_errors,
            "response_time_stats": response_time_stats,
            "active_alerts": len(active_alerts),
            "alerts": [
                {
                    "name": alert.name,
                    "severity": alert.severity.value,
                    "message": alert.message,
                    "timestamp": alert.timestamp.isoformat()
                }
                for alert in active_alerts
            ]
        }

# Global monitoring instances
metrics_collector = MetricsCollector()
alert_manager = AlertManager()
system_monitor = SystemMonitor(metrics_collector, alert_manager)
app_monitor = ApplicationMonitor(metrics_collector, alert_manager)

# Notification handlers
def slack_notification_handler(alert: Alert):
    """Send alert to Slack (placeholder - requires webhook URL)"""
    webhook_url = os.getenv("SLACK_WEBHOOK_URL")
    if not webhook_url:
        logger.debug("Slack webhook URL not configured")
        return
    
    # TODO: Implement actual Slack notification
    logger.info(f"Would send Slack notification: {alert.name} - {alert.message}")

def email_notification_handler(alert: Alert):
    """Send alert via email (placeholder)"""
    # TODO: Implement email notification
    logger.info(f"Would send email notification: {alert.name} - {alert.message}")

# Register notification handlers
alert_manager.add_notification_handler(slack_notification_handler)
alert_manager.add_notification_handler(email_notification_handler)

def start_monitoring():
    """Start background monitoring tasks"""
    import threading
    import time
    
    def monitoring_loop():
        while True:
            try:
                system_monitor.collect_system_metrics()
                time.sleep(60)  # Collect metrics every minute
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(60)
    
    # Start monitoring in background thread
    monitoring_thread = threading.Thread(target=monitoring_loop, daemon=True)
    monitoring_thread.start()
    logger.info("Monitoring started")

# Context managers for tracking operations
class track_operation:
    """Context manager for tracking operation metrics"""
    
    def __init__(self, operation_name: str, tags: Dict[str, str] = None):
        self.operation_name = operation_name
        self.tags = tags or {}
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        success = exc_type is None
        
        self.tags["success"] = str(success)
        metrics_collector.timer(f"{self.operation_name}.duration", duration, self.tags)
        metrics_collector.increment(f"{self.operation_name}.total", tags=self.tags)
        
        if not success:
            metrics_collector.increment(f"{self.operation_name}.errors", tags=self.tags)

class track_http_request:
    """Context manager for tracking HTTP request metrics"""
    
    def __init__(self, endpoint: str, method: str):
        self.endpoint = endpoint
        self.method = method
        self.start_time = None
        self.status_code = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def set_status_code(self, status_code: int):
        self.status_code = status_code
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        status_code = self.status_code or (500 if exc_type else 200)
        
        app_monitor.track_request(self.endpoint, self.method, status_code, duration)