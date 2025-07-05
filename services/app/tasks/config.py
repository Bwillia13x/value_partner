"""Celery configuration settings"""
import os
from datetime import timedelta

# Broker settings
broker_url = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
result_backend = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/1')

# Task settings
task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']
timezone = 'UTC'
enable_utc = True

# Worker settings
worker_concurrency = int(os.getenv('CELERY_WORKER_CONCURRENCY', 4))
worker_max_tasks_per_child = 100
worker_prefetch_multiplier = 1  # Fair task distribution

# Task timeouts
task_time_limit = 30 * 60  # 30 minutes
task_soft_time_limit = 25 * 60  # 25 minutes

# Beat settings (for scheduled tasks)
beat_scheduler = 'celery.beat.PersistentScheduler'
beat_schedule = {}

# Result backend settings
result_expires = timedelta(days=7)  # Keep results for 7 days
result_persistent = True

# Security settings
worker_send_task_events = True
task_send_sent_event = True
event_queue_expires = 60  # 1 minute
event_queue_ttl = 5  # 5 seconds

# Logging
worker_redirect_stdouts = True
worker_redirect_stdouts_level = 'INFO'
worker_log_format = '''[%(asctime)s: %(levelname)s/%(processName)s] %(message)s'''

# Error emails (if configured)
if os.getenv('CELERY_SEND_TASK_ERROR_EMAILS', 'false').lower() == 'true':
    ADMINS = [
        ('Admin', os.getenv('ADMIN_EMAIL', 'admin@example.com')),
    ]
    server_email = os.getenv('SERVER_EMAIL', 'noreply@valuepartner.app')
    email_backend = 'django.core.mail.backends.smtp.EmailBackend'
    email_host = os.getenv('EMAIL_HOST', 'smtp.sendgrid.net')
    email_port = int(os.getenv('EMAIL_PORT', 587))
    email_use_tls = os.getenv('EMAIL_USE_TLS', 'true').lower() == 'true'
    email_host_user = os.getenv('EMAIL_HOST_USER', 'apikey')
    email_host_password = os.getenv('EMAIL_HOST_PASSWORD', '')
    
    # Configure error emails
    from celery.signals import task_failure
    
    @task_failure.connect
    def celery_task_failure_email(**kwargs):
        from django.core.mail import mail_admins
        
        task = kwargs.get('sender')
        task_id = kwargs.get('task_id')
        exception = kwargs.get('exception')
        args = kwargs.get('args', [])
        kwargs_data = kwargs.get('kwargs', {})
        traceback = kwargs.get('traceback')
        
        subject = f'Celery Task Failed: {task}'
        message = f"""
        Task {task.name} ({task_id}) failed with exception: {exception!r}
        
        Task was called with:
        args: {args}
        kwargs: {kwargs_data}
        
        Traceback:
        {traceback}
        """
        
        mail_admins(subject, message, fail_silently=True)
