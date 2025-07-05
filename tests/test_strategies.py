"""Test strategies functionality with proper test isolation."""
import pytest

def test_create_strategy(authenticated_client):
    """Test creating a new strategy."""
    response = authenticated_client.post(
        "/strategies/",
        json={
            "name": "Growth", 
            "description": "Growth strategy", 
            "holdings": [
                {"symbol": "AAPL", "target_weight": 0.5}, 
                {"symbol": "GOOG", "target_weight": 0.5}
            ]
        },
    )
    assert response.status_code == 200, f"Strategy creation failed: {response.text}"
    data = response.json()
    assert data["name"] == "Growth"
    assert len(data["holdings"]) == 2
    assert data["holdings"][0]["symbol"] == "AAPL"
    assert data["holdings"][1]["symbol"] == "GOOG"

def test_read_strategies(authenticated_client):
    """Test reading strategies - this was the failing test due to lack of isolation."""
    # First, verify no strategies exist initially (fresh database per test)
    initial_response = authenticated_client.get("/strategies/")
    assert initial_response.status_code == 200
    initial_data = initial_response.json()
    assert len(initial_data) == 0, f"Expected 0 strategies initially, found {len(initial_data)}"
    
    # Create a strategy
    create_response = authenticated_client.post(
        "/strategies/",
        json={
            "name": "Growth", 
            "description": "Growth strategy", 
            "holdings": [
                {"symbol": "AAPL", "target_weight": 0.5}, 
                {"symbol": "GOOG", "target_weight": 0.5}
            ]
        },
    )
    assert create_response.status_code == 200, f"Strategy creation failed: {create_response.text}"
    
    # Now verify we have exactly 1 strategy
    response = authenticated_client.get("/strategies/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1, f"Expected exactly 1 strategy, found {len(data)}"
    assert data[0]["name"] == "Growth"

def test_rebalance_strategy(authenticated_client):
    """Test strategy rebalancing functionality."""
    # Create a strategy
    strategy_response = authenticated_client.post(
        "/strategies/",
        json={
            "name": "Value", 
            "description": "Value strategy", 
            "holdings": [{"symbol": "MSFT", "target_weight": 1.0}]
        },
    )
    assert strategy_response.status_code == 200, f"Strategy creation failed: {strategy_response.text}"
    strategy_id = strategy_response.json()["id"]

    # Test rebalancing the strategy
    response = authenticated_client.post(f"/strategies/{strategy_id}/rebalance")
    assert response.status_code == 200
    data = response.json()
    assert "proposed_trades" in data
    assert "executed_trades" in data


def test_multiple_strategies_isolation(authenticated_client):
    """Test that multiple strategy operations work with proper isolation."""
    # Create first strategy
    response1 = authenticated_client.post(
        "/strategies/",
        json={
            "name": "Growth Strategy", 
            "description": "Growth focused", 
            "holdings": [{"symbol": "AAPL", "target_weight": 1.0}]
        },
    )
    assert response1.status_code == 200
    
    # Create second strategy
    response2 = authenticated_client.post(
        "/strategies/",
        json={
            "name": "Value Strategy", 
            "description": "Value focused", 
            "holdings": [{"symbol": "MSFT", "target_weight": 1.0}]
        },
    )
    assert response2.status_code == 200
    
    # Verify we have exactly 2 strategies
    list_response = authenticated_client.get("/strategies/")
    assert list_response.status_code == 200
    strategies = list_response.json()
    assert len(strategies) == 2, f"Expected exactly 2 strategies, found {len(strategies)}"
    
    strategy_names = [s["name"] for s in strategies]
    assert "Growth Strategy" in strategy_names
    assert "Value Strategy" in strategy_names


def test_strategy_isolation_between_tests(authenticated_client):
    """Test that this test starts with a clean database (no strategies from previous tests)."""
    # This test should always start with 0 strategies due to proper isolation
    response = authenticated_client.get("/strategies/")
    assert response.status_code == 200
    strategies = response.json()
    assert len(strategies) == 0, f"Expected 0 strategies due to test isolation, found {len(strategies)}"