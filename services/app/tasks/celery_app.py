"""Celery application configuration and setup"""
import os
from celery import Celery
from celery.schedules import crontab
from datetime import timedelta

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('CELERY_CONFIG_MODULE', 'app.tasks.config')

# Create the Celery app
app = Celery('value_partner')

# Load configuration from Django settings
app.config_from_envvar('CELERY_CONFIG_MODULE')

# Auto-discover tasks in all installed apps
autodiscover_tasks = ['app.tasks.reconciliation']

# Configure beat schedule
app.conf.beat_schedule = {
    'reconcile-accounts-daily': {
        'task': 'app.tasks.reconciliation.reconcile_all_accounts',
        'schedule': crontab(hour=1, minute=0),  # Run daily at 1 AM
        'options': {'expires': 60 * 60},  # Expire after 1 hour if not picked up
    },
    'sync-market-data-hourly': {
        'task': 'app.tasks.reconciliation.sync_market_data',
        'schedule': timedelta(hours=1),  # Run every hour
        'options': {'expires': 30 * 60},  # Expire after 30 minutes if not picked up
    },
}

# Set timezone
app.conf.timezone = 'UTC'

if __name__ == '__main__':
    app.start()
