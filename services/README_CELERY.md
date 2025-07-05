# Celery Task Queue for Value Partner

This document provides an overview of the Celery task queue implementation for the Value Partner platform, including setup instructions, architecture, and usage examples.

## Overview

The Celery task queue is used for background processing of long-running or periodic tasks, such as:

- Daily reconciliation of investment accounts
- Synchronization of market data
- Batch processing of portfolio analytics
- Email notifications and alerts

## Prerequisites

- Python 3.8+
- Redis server (for message broker and result backend)
- Required Python packages (install via `pip install -r requirements.txt`)

## Configuration

Environment variables are used for configuration. Copy `.env.example` to `.env` and update the values as needed:

```bash
cp .env.example .env
```

Key configuration options:

```env
# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
CELERY_WORKER_CONCURRENCY=4
CELERY_LOG_LEVEL=info

# Email Configuration (for error notifications)
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USE_TLS=true
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=your_sendgrid_api_key
ADMIN_EMAIL=admin@example.com
SERVER_EMAIL=noreply@valuepartner.app
```

## Running Celery

### Development

1. Start Redis server (if not already running):
   ```bash
   redis-server
   ```

2. Start Celery worker and beat in separate terminals:
   ```bash
   # Terminal 1 - Worker
   python run_celery.py worker
   
   # Terminal 2 - Beat (scheduler)
   python run_celery.py beat
   ```

   Or start both in a single terminal:
   ```bash
   python run_celery.py
   ```

### Production

For production, use a process manager like systemd or supervisor. Example systemd service files:

**/etc/systemd/system/celery-worker.service**
```ini
[Unit]
Description=Celery Worker Service
After=network.target redis-server.service

[Service]
Type=simple
User=www-data
Group=www-data
EnvironmentFile=/path/to/your/.env
WorkingDirectory=/path/to/value_partner/services
ExecStart=/usr/bin/python3 run_celery.py worker --loglevel=info
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

**/etc/systemd/system/celery-beat.service**
```ini
[Unit]
Description=Celery Beat Service
After=network.target redis-server.service

[Service]
Type=simple
User=www-data
Group=www-data
EnvironmentFile=/path/to/your/.env
WorkingDirectory=/path/to/value_partner/services
ExecStart=/usr/bin/python3 run_celery.py beat --loglevel=info
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

## Available Tasks

### Reconciliation Tasks

- `app.tasks.reconciliation.reconcile_all_accounts`: Reconcile all active accounts
- `app.tasks.reconciliation.reconcile_account(account_id, user_id)`: Reconcile a specific account
- `app.tasks.reconciliation.sync_market_data()`: Sync market data for all tracked securities

### Scheduled Tasks

Tasks are scheduled in `app/tasks/celery_app.py`:

```python
app.conf.beat_schedule = {
    'reconcile-accounts-daily': {
        'task': 'app.tasks.reconciliation.reconcile_all_accounts',
        'schedule': crontab(hour=1, minute=0),  # Run daily at 1 AM
    },
    'sync-market-data-hourly': {
        'task': 'app.tasks.reconciliation.sync_market_data',
        'schedule': timedelta(hours=1),  # Run every hour
    },
}
```

## Monitoring

### Flower

Flower is a web-based tool for monitoring Celery. To start Flower:

```bash
celery -A app.tasks.celery_app flower --port=5555
```

Access the dashboard at http://localhost:5555

### Logs

Logs are written to the `logs/` directory by default:

- `logs/celery-worker.log`: Worker logs
- `logs/celery-beat.log`: Beat scheduler logs

## Testing

Run the test script to verify the reconciliation flow:

```bash
python test_reconciliation.py
```

## Troubleshooting

### Common Issues

1. **Celery can't connect to Redis**
   - Ensure Redis is running: `redis-cli ping`
   - Verify the Redis URL in `.env` matches your Redis configuration

2. **Tasks not being picked up by workers**
   - Check that the worker is running: `ps aux | grep celery`
   - Verify the task is properly registered: `celery -A app.tasks.celery_app inspect registered`

3. **Scheduled tasks not running**
   - Check the beat scheduler logs: `tail -f logs/celery-beat.log`
   - Verify the schedule in `celery_app.py`

## Adding New Tasks

1. Create a new task function in the appropriate module under `app/tasks/`
2. Decorate it with `@shared_task`
3. Import the task in `app/tasks/__init__.py`
4. If it's a scheduled task, add it to `celery_app.py`

Example task:

```python
from celery import shared_task

@shared_task
def process_data(data):
    """Example background task"""
    # Process data here
    return {"status": "success", "processed": len(data)}
```
