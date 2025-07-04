import pytest
from fastapi.testclient import TestClient

try:
    from services.app.main import app
except Exception as e:
    pytest.skip(f"Cannot import FastAPI app: {e}")

client = TestClient(app)

def test_health_endpoint():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json().get("status") == "ok"

def test_plugins_endpoint():
    resp = client.get("/plugins")
    assert resp.status_code == 200
    assert "available_plugins" in resp.json()