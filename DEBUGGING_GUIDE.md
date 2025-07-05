# Debugging Guide for Value Partner Application

## Overview

This guide provides comprehensive debugging strategies and tools for the Value Partner application. The debugging infrastructure has been enhanced with request tracing, structured logging, error handling, and performance monitoring.

## Key Debugging Features Implemented

### 1. Request Tracing
- **Correlation IDs**: Every request receives a unique `request_id` for tracking
- **Request Headers**: Responses include `X-Request-ID` header
- **Structured Logging**: All logs include request context

### 2. Enhanced Error Handling
- **Centralized Error Handler**: `services/app/error_handling.py`
- **Error Categories**: NETWORK, DATABASE, AUTHENTICATION, VALIDATION, BUSINESS_LOGIC, EXTERNAL_API, SYSTEM
- **Error Severity**: LOW, MEDIUM, HIGH, CRITICAL
- **Circuit Breaker Pattern**: Automatic fault isolation
- **Retry Logic**: Exponential backoff for transient failures

### 3. Structured Logging
- **JSON Logging**: Machine-readable log format
- **Log Rotation**: 10MB files with 5 backups
- **Separate Error Logs**: Dedicated error file for quick analysis
- **Context Preservation**: Request IDs and user context in all logs

### 4. Health Monitoring
- **Basic Health Check**: `/health` - Simple status check
- **Detailed Health Check**: `/health/detailed` - Comprehensive service status
- **Error Metrics**: Error rates and circuit breaker status
- **Service Dependencies**: Database, Celery worker status

### 5. Performance Monitoring
- **Function-Level Monitoring**: Execution time, memory usage, CPU usage
- **Performance Thresholds**: Automatic warnings for slow operations
- **Metrics Dashboard**: `/admin/performance` endpoint
- **Historical Data**: Last 100 executions per function

## Debugging Workflow

### 1. Immediate Issue Response

When an issue occurs:

1. **Check Health Status**:
   ```bash
   curl http://localhost:8000/health/detailed
   ```

2. **Review Recent Logs**:
   ```bash
   tail -f services/logs/errors.log | jq .
   ```

3. **Check Error Rates**:
   ```bash
   grep "ERROR" services/logs/app.log | tail -20
   ```

### 2. Request Tracing

For debugging specific user issues:

1. **Find Request ID**: Look for `X-Request-ID` in response headers
2. **Trace Request**: Search logs for the request ID
   ```bash
   grep "request_id_here" services/logs/app.log | jq .
   ```

### 3. Performance Analysis

For performance issues:

1. **Check Performance Metrics**:
   ```bash
   curl http://localhost:8000/admin/performance
   ```

2. **Monitor Function Performance**:
   - Look for functions exceeding thresholds
   - Check memory usage trends
   - Analyze execution time patterns

### 4. Error Investigation

For systematic errors:

1. **Review Error Categories**: Check which error types are most common
2. **Check Circuit Breakers**: See if any services are automatically blocked
3. **Analyze Error Context**: Review user_id, account_id, function_name in error records

## Critical Areas to Monitor

### 1. Database Operations
- **Connection Pool**: Monitor pool utilization
- **Query Performance**: Watch for slow queries
- **Transaction Rollbacks**: Track failed transactions

**Debugging Commands**:
```python
# Check database connection health
from services.app.database import get_db
db = next(get_db())
db.execute("SELECT 1").fetchone()
```

### 2. External API Integrations
- **Plaid Service**: Account linking and data sync
- **Market Data**: Quote fetching and real-time updates
- **Alpaca**: Order execution (when enabled)

**Debugging Commands**:
```python
# Test Plaid connectivity
from services.app.plaid_client import plaid_client
response = plaid_client.create_link_token(1, "Test User")
```

### 3. Background Tasks (Celery)
- **Worker Health**: Ensure workers are running
- **Queue Depth**: Monitor task backlog
- **Task Failures**: Track failed reconciliation tasks

**Debugging Commands**:
```bash
# Check Celery worker status
celery -A services.app.tasks.celery_app inspect active
celery -A services.app.tasks.celery_app inspect stats
```

### 4. Real-time Synchronization
- **WebSocket Connections**: Monitor connection count
- **Memory Leaks**: Watch for accumulating connections
- **Data Consistency**: Verify portfolio sync accuracy

### 5. Order Management
- **Order Lifecycle**: Track order state transitions
- **Broker Integration**: Monitor order submission success rates
- **Risk Management**: Validate position limits

## Log Analysis

### Log Structure
```json
{
  "timestamp": "2024-01-01T12:00:00.000Z",
  "level": "INFO",
  "name": "services.app",
  "message": "Request completed: 200",
  "request_id": "123e4567-e89b-12d3-a456-426614174000",
  "user_id": 123,
  "function_name": "create_link_token",
  "status_code": 200
}
```

### Common Log Queries

1. **Find all errors for a user**:
   ```bash
   grep '"user_id": 123' services/logs/errors.log | jq .
   ```

2. **Find slow operations**:
   ```bash
   grep '"execution_time"' services/logs/app.log | jq 'select(.execution_time > 5)'
   ```

3. **Check external API failures**:
   ```bash
   grep '"category": "EXTERNAL_API"' services/logs/errors.log | jq .
   ```

## Error Recovery Procedures

### 1. Database Connection Issues
- **Restart Connection Pool**: Application restart may be required
- **Check Database Status**: Verify database service is running
- **Review Connection Limits**: Ensure connection pool is properly sized

### 2. External Service Failures
- **Circuit Breaker Status**: Check if automatic blocking is active
- **Manual Reset**: Reset circuit breakers if needed
- **Fallback Procedures**: Use cached data when available

### 3. Background Task Failures
- **Restart Workers**: Restart Celery workers
- **Clear Queue**: Remove problematic tasks
- **Manual Reconciliation**: Run account sync manually

### 4. Memory Issues
- **Restart Application**: Clear accumulated memory
- **Check Subscriptions**: Clean up WebSocket connections
- **Review Cache Size**: Ensure caches have proper limits

## Environment Setup for Debugging

### Required Environment Variables
```bash
# Security
SECRET_KEY=your_secure_secret_key_here

# Database
DATABASE_URL=sqlite:///./portfolio.db

# External Services
PLAID_CLIENT_ID=your_plaid_client_id
PLAID_SECRET=your_plaid_secret
PLAID_ENV=sandbox

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

### Development Tools

1. **Enable Debug Logging**:
   ```python
   import logging
   logging.getLogger('services.app').setLevel(logging.DEBUG)
   ```

2. **Database Query Logging**:
   ```python
   # In database.py
   engine = create_engine(DATABASE_URL, echo=True)  # Enable SQL logging
   ```

3. **Performance Profiling**:
   ```python
   from services.app.performance_monitor import monitor_performance
   
   @monitor_performance("custom_function")
   def my_function():
       # Your code here
       pass
   ```

## Production Monitoring

### Key Metrics to Track
- **Error Rate**: < 0.1% for critical operations
- **Response Time**: < 200ms for API endpoints
- **Database Performance**: < 50ms for 95th percentile queries
- **External API Success Rate**: > 99.5%
- **Background Task Success Rate**: > 99%

### Alerting Thresholds
- Database connection pool > 80% utilization
- API response time > 5 seconds
- Celery queue depth > 100 tasks
- Memory usage > 80% of available
- Error rate > 1% over 5 minutes

### Integration with Monitoring Tools

For production environments, integrate with:
- **APM**: Datadog, New Relic, or similar
- **Log Aggregation**: ELK Stack, Splunk
- **Error Tracking**: Sentry
- **Uptime Monitoring**: Pingdom, StatusCake

## Security Considerations

### Fixed Security Issues
- **SECRET_KEY**: Moved to environment variables (CRITICAL fix applied)
- **Input Validation**: Enhanced through error handling
- **Error Information**: Sanitized error responses to prevent information leakage

### Ongoing Security Monitoring
- Track authentication failures
- Monitor for suspicious API usage patterns
- Log all security-related events
- Regular security audits of error logs

## Getting Help

For debugging assistance:
1. Check recent error logs first
2. Review health check status
3. Analyze performance metrics
4. Provide request ID when reporting issues
5. Include relevant log entries and error context

This debugging infrastructure provides comprehensive visibility into the Value Partner application's behavior and should significantly reduce time to resolution for issues.