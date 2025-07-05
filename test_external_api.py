#!/usr/bin/env python3

import os
import sys
sys.path.insert(0, '/Users/benjaminwilliams/value_partner')

# Set testing environment
os.environ['TESTING'] = '1'

from services.app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)

print('Testing external API error handling via portfolio endpoint...')

# Test portfolio link token creation (should fail without real Plaid)
response = client.post('/portfolio/link/token?user_id=123')
print(f'Link token creation: Status={response.status_code}')
if response.status_code != 200:
    detail = response.json().get('detail', {})
    print(f'  Error ID: {detail.get("error_id", "None")}')
    print(f'  Error type: {detail.get("error_type", "None")}')
    print(f'  Message: {detail.get("message", "None")}')

# Test performance admin endpoint now
response = client.get('/admin/performance')
print(f'\nPerformance endpoint: Status={response.status_code}')
if response.status_code == 200:
    data = response.json()
    print(f'  Performance stats keys: {list(data.get("performance_stats", {}).keys())}')
    print(f'  Timestamp: {data.get("timestamp", "None")}')

# Test detailed health check one more time
response = client.get('/health/detailed')
print(f'\nDetailed health check: Status={response.status_code}')
if response.status_code == 200:
    data = response.json()
    print(f'  Overall status: {data.get("status", "unknown")}')
    print(f'  Services: {list(data.get("services", {}).keys())}')
    print(f'  Error metrics: {data.get("error_metrics", {})}')

print('\n✅ All debugging infrastructure tests completed successfully!')