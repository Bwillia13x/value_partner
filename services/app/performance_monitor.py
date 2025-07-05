"""Performance monitoring utilities for critical functions"""
import time
import logging
from functools import wraps
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import psutil
import os

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetrics:
    function_name: str
    execution_time: float
    memory_usage_mb: float
    cpu_percent: float
    timestamp: datetime
    status: str
    error: Optional[str] = None

class PerformanceMonitor:
    """Performance monitoring for critical functions"""
    
    def __init__(self):
        self.metrics: Dict[str, list] = {}
        self.thresholds = {
            'execution_time': 5.0,  # seconds
            'memory_usage_mb': 500.0,  # MB
            'cpu_percent': 80.0  # percentage
        }
    
    def record_metric(self, metric: PerformanceMetrics):
        """Record a performance metric"""
        if metric.function_name not in self.metrics:
            self.metrics[metric.function_name] = []
        
        self.metrics[metric.function_name].append(metric)
        
        # Keep only last 100 metrics per function
        if len(self.metrics[metric.function_name]) > 100:
            self.metrics[metric.function_name] = self.metrics[metric.function_name][-100:]
        
        # Check thresholds and log warnings
        self._check_thresholds(metric)
    
    def _check_thresholds(self, metric: PerformanceMetrics):
        """Check if metric exceeds thresholds"""
        warnings = []
        
        if metric.execution_time > self.thresholds['execution_time']:
            warnings.append(f"Slow execution: {metric.execution_time:.2f}s")
        
        if metric.memory_usage_mb > self.thresholds['memory_usage_mb']:
            warnings.append(f"High memory usage: {metric.memory_usage_mb:.2f}MB")
        
        if metric.cpu_percent > self.thresholds['cpu_percent']:
            warnings.append(f"High CPU usage: {metric.cpu_percent:.1f}%")
        
        if warnings:
            logger.warning(f"Performance threshold exceeded in {metric.function_name}: {', '.join(warnings)}")
    
    def get_function_stats(self, function_name: str) -> Dict[str, Any]:
        """Get statistics for a specific function"""
        if function_name not in self.metrics:
            return {}
        
        metrics = self.metrics[function_name]
        execution_times = [m.execution_time for m in metrics if m.status == 'success']
        
        if not execution_times:
            return {"error": "No successful executions recorded"}
        
        return {
            "total_calls": len(metrics),
            "successful_calls": len(execution_times),
            "failed_calls": len(metrics) - len(execution_times),
            "avg_execution_time": sum(execution_times) / len(execution_times),
            "min_execution_time": min(execution_times),
            "max_execution_time": max(execution_times),
            "avg_memory_usage": sum(m.memory_usage_mb for m in metrics) / len(metrics),
            "avg_cpu_usage": sum(m.cpu_percent for m in metrics) / len(metrics)
        }
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all monitored functions"""
        return {func_name: self.get_function_stats(func_name) 
                for func_name in self.metrics.keys()}

# Global performance monitor instance
performance_monitor = PerformanceMonitor()

def monitor_performance(func_name: Optional[str] = None):
    """Decorator to monitor function performance"""
    def decorator(func):
        function_name = func_name or f"{func.__module__}.{func.__name__}"
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            process = psutil.Process(os.getpid())
            start_time = time.time()
            start_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            try:
                result = await func(*args, **kwargs)
                status = "success"
                error = None
            except Exception as e:
                result = None
                status = "error"
                error = str(e)
                raise
            finally:
                end_time = time.time()
                end_memory = process.memory_info().rss / 1024 / 1024  # MB
                cpu_percent = process.cpu_percent()
                
                metric = PerformanceMetrics(
                    function_name=function_name,
                    execution_time=end_time - start_time,
                    memory_usage_mb=end_memory - start_memory,
                    cpu_percent=cpu_percent,
                    timestamp=datetime.utcnow(),
                    status=status,
                    error=error
                )
                
                performance_monitor.record_metric(metric)
                
                logger.info(f"Performance: {function_name}", extra={
                    "function": function_name,
                    "execution_time": metric.execution_time,
                    "memory_usage_mb": metric.memory_usage_mb,
                    "cpu_percent": metric.cpu_percent,
                    "status": status
                })
            
            return result
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            process = psutil.Process(os.getpid())
            start_time = time.time()
            start_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            try:
                result = func(*args, **kwargs)
                status = "success"
                error = None
            except Exception as e:
                result = None
                status = "error"
                error = str(e)
                raise
            finally:
                end_time = time.time()
                end_memory = process.memory_info().rss / 1024 / 1024  # MB
                cpu_percent = process.cpu_percent()
                
                metric = PerformanceMetrics(
                    function_name=function_name,
                    execution_time=end_time - start_time,
                    memory_usage_mb=end_memory - start_memory,
                    cpu_percent=cpu_percent,
                    timestamp=datetime.utcnow(),
                    status=status,
                    error=error
                )
                
                performance_monitor.record_metric(metric)
                
                logger.info(f"Performance: {function_name}", extra={
                    "function": function_name,
                    "execution_time": metric.execution_time,
                    "memory_usage_mb": metric.memory_usage_mb,
                    "cpu_percent": metric.cpu_percent,
                    "status": status
                })
            
            return result
        
        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator