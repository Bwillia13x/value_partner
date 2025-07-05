#!/usr/bin/env python3

import logging
import os
from services.app.logging_config import setup_logging

# Test logging functionality
print("Testing logging functionality...")

# Set up logging
logger = setup_logging()

# Test different log levels
logger.debug("Debug message with extra data", extra={'component': 'test', 'user_id': 123})
logger.info("Info message", extra={'action': 'test_logging', 'status': 'success'})
logger.warning("Warning message", extra={'threshold_exceeded': True, 'value': 85})
logger.error("Error message", extra={'error_type': 'test_error', 'retry_count': 1})

print("✅ Log messages sent")

# Check if log files exist
log_dir = os.path.join(os.path.dirname(__file__), "services", "logs")
print(f"Checking log directory: {log_dir}")

if os.path.exists(log_dir):
    files = os.listdir(log_dir)
    print(f"Log files found: {files}")
    
    # Try to read log content
    app_log = os.path.join(log_dir, "app.log")
    if os.path.exists(app_log):
        print(f"\n=== App Log Content ===")
        with open(app_log, 'r') as f:
            print(f.read())
    
    error_log = os.path.join(log_dir, "errors.log")
    if os.path.exists(error_log):
        print(f"\n=== Error Log Content ===")
        with open(error_log, 'r') as f:
            print(f.read())
else:
    print("❌ Log directory not found")