import logging
import logging.config
import os
import re
from datetime import datetime

class SensitiveDataFilter(logging.Filter):
    """Filter to remove sensitive data from log messages"""
    
    # Patterns to match sensitive data
    SENSITIVE_PATTERNS = [
        # Password patterns - improved to catch more variations
        (r'password["\']?\s*[:=]\s*["\']?([^"\'&\s]+)["\']?', 'password=***'),
        (r'pass["\']?\s*[:=]\s*["\']?([^"\'&\s]+)["\']?', 'pass=***'),
        (r'pwd["\']?\s*[:=]\s*["\']?([^"\'&\s]+)["\']?', 'pwd=***'),
        (r'User password is\s+([^\s]+)', 'User password is ***'),
        (r'password\s+is\s+([^\s]+)', 'password is ***'),
        
        # Token patterns
        (r'token["\']?\s*[:=]\s*["\']?([^"\'&\s]+)["\']?', 'token=***'),
        (r'access_token["\']?\s*[:=]\s*["\']?([^"\'&\s]+)["\']?', 'access_token=***'),
        (r'refresh_token["\']?\s*[:=]\s*["\']?([^"\'&\s]+)["\']?', 'refresh_token=***'),
        (r'bearer["\']?\s*[:=]\s*["\']?([^"\'&\s]+)["\']?', 'bearer=***'),
        (r'Access token:\s*([^\s]+)', 'Access token: ***'),
        
        # API key patterns - improved to catch more variations
        (r'api_key["\']?\s*[:=]\s*["\']?([^"\'&\s]+)["\']?', 'api_key=***'),
        (r'apikey["\']?\s*[:=]\s*["\']?([^"\'&\s]+)["\']?', 'apikey=***'),
        (r'API key:\s*([^\s]+)', 'API key: ***'),
        (r'key["\']?\s*[:=]\s*["\']?([A-Za-z0-9_-]{20,})["\']?', 'key=***'),
        (r'sk_[a-zA-Z0-9_-]+', 'sk_***'),  # Stripe/similar secret keys
        
        # Secret patterns
        (r'secret["\']?\s*[:=]\s*["\']?([^"\'&\s]+)["\']?', 'secret=***'),
        (r'SECRET_KEY["\']?\s*[:=]\s*["\']?([^"\'&\s]+)["\']?', 'SECRET_KEY=***'),
        
        # Credit card patterns
        (r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b', '****-****-****-****'),
        (r'\b\d{13,19}\b', '****-****-****-****'),
        
        # SSN patterns
        (r'\b\d{3}-\d{2}-\d{4}\b', '***-**-****'),
        (r'\b\d{9}\b', '*********'),
        
        # Email patterns (partial sanitization)
        (r'([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', r'\1***@***.\2'),
        
        # Plaid access token patterns
        (r'access-[a-zA-Z0-9-]{20,}', 'access-***'),
        
        # Generic sensitive data in JSON
        (r'"(password|token|secret|key|api_key)"\s*:\s*"([^"]+)"', r'"\1": "***"'),
        
        # Authorization headers
        (r'Authorization:\s*Bearer\s+([^\s]+)', 'Authorization: Bearer ***'),
        (r'Authorization:\s*([^\s]+)', 'Authorization: ***'),
    ]
    
    def filter(self, record):
        """Filter out sensitive data from log records"""
        if hasattr(record, 'msg'):
            # Sanitize the main message
            record.msg = self._sanitize_message(str(record.msg))
            
        # Sanitize arguments if they exist
        if hasattr(record, 'args') and record.args:
            sanitized_args = []
            for arg in record.args:
                if isinstance(arg, str):
                    sanitized_args.append(self._sanitize_message(arg))
                else:
                    sanitized_args.append(arg)
            record.args = tuple(sanitized_args)
        
        return True
    
    def _sanitize_message(self, message):
        """Apply sanitization patterns to a message"""
        for pattern, replacement in self.SENSITIVE_PATTERNS:
            message = re.sub(pattern, replacement, message, flags=re.IGNORECASE)
        return message

def _json_formatter_class():
    """Return JsonFormatter class if available, else standard Formatter path string."""
    try:
        import pythonjsonlogger.jsonlogger as _jj  # type: ignore
        return 'pythonjsonlogger.jsonlogger.JsonFormatter'
    except ImportError:  # pragma: no cover
        return 'logging.Formatter'

def setup_logging():
    """Configure structured logging for the application"""
    
    # Create logs directory if it doesn't exist
    log_dir = os.path.join(os.path.dirname(__file__), "..", "logs")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Configure logging
    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'detailed': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            },
            'json': {
                'format': '%(asctime)s %(name)s %(levelname)s %(message)s',
                'class': _json_formatter_class()
            }
        },
        'filters': {
            'sensitive_data': {
                '()': SensitiveDataFilter,
            }
        },
        'handlers': {
            'console': {
                'class': 'logging.StreamHandler',
                'level': 'INFO',
                'formatter': 'detailed',
                'filters': ['sensitive_data'],
                'stream': 'ext://sys.stdout'
            },
            'file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'DEBUG',
                'formatter': 'detailed',
                'filters': ['sensitive_data'],
                'filename': f'{log_dir}/app.log',
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5
            },
            'error_file': {
                'class': 'logging.handlers.RotatingFileHandler',
                'level': 'ERROR',
                'formatter': 'detailed',
                'filters': ['sensitive_data'],
                'filename': f'{log_dir}/errors.log',
                'maxBytes': 10485760,  # 10MB
                'backupCount': 5
            }
        },
        'loggers': {
            'services.app': {
                'level': 'DEBUG',
                'handlers': ['console', 'file', 'error_file'],
                'propagate': False
            },
            'sqlalchemy.engine': {
                'level': 'INFO',
                'handlers': ['file'],
                'propagate': False
            },
            'celery': {
                'level': 'INFO',
                'handlers': ['console', 'file'],
                'propagate': False
            }
        },
        'root': {
            'level': 'INFO',
            'handlers': ['console', 'file']
        }
    }
    
    logging.config.dictConfig(logging_config)
    
    # Set up custom logger for structured logging
    logger = logging.getLogger('services.app')
    logger.info("Logging configuration initialized with sensitive data filtering", extra={
        "component": "logging_config",
        "timestamp": datetime.utcnow().isoformat()
    })
    
    return logger