"""Test isolation validation to demonstrate the fix for the test database issue."""
import pytest


class TestIsolationValidation:
    """Test class to validate that test isolation is working properly."""
    
    def test_isolation_1_create_strategy(self, authenticated_client):
        """First test - create a strategy and verify count."""
        # Should start with empty database
        response = authenticated_client.get("/strategies/")
        assert response.status_code == 200
        strategies = response.json()
        assert len(strategies) == 0, f"Test 1: Expected 0 strategies initially, found {len(strategies)}"
        
        # Create a strategy
        create_response = authenticated_client.post(
            "/strategies/",
            json={
                "name": "Test Strategy 1", 
                "description": "First test strategy", 
                "holdings": [{"symbol": "AAPL", "target_weight": 1.0}]
            },
        )
        assert create_response.status_code == 200
        
        # Verify we now have 1 strategy
        response = authenticated_client.get("/strategies/")
        assert response.status_code == 200
        strategies = response.json()
        assert len(strategies) == 1, f"Test 1: Expected 1 strategy after creation, found {len(strategies)}"
        assert strategies[0]["name"] == "Test Strategy 1"
    
    def test_isolation_2_fresh_database(self, authenticated_client):
        """Second test - should start with fresh database (0 strategies)."""
        # This test should see a completely clean database
        # If test isolation is working, there should be no strategies from test 1
        response = authenticated_client.get("/strategies/")
        assert response.status_code == 200
        strategies = response.json()
        assert len(strategies) == 0, f"Test 2: Expected 0 strategies due to isolation, found {len(strategies)}"
        
        # Create a different strategy
        create_response = authenticated_client.post(
            "/strategies/",
            json={
                "name": "Test Strategy 2", 
                "description": "Second test strategy", 
                "holdings": [{"symbol": "MSFT", "target_weight": 1.0}]
            },
        )
        assert create_response.status_code == 200
        
        # Verify we have exactly 1 strategy (not 2 from previous test)
        response = authenticated_client.get("/strategies/")
        assert response.status_code == 200
        strategies = response.json()
        assert len(strategies) == 1, f"Test 2: Expected 1 strategy, found {len(strategies)}"
        assert strategies[0]["name"] == "Test Strategy 2"
    
    def test_isolation_3_verify_clean_slate(self, authenticated_client):
        """Third test - verify isolation continues to work."""
        # Again, should start with empty database
        response = authenticated_client.get("/strategies/")
        assert response.status_code == 200
        strategies = response.json()
        assert len(strategies) == 0, f"Test 3: Expected 0 strategies due to isolation, found {len(strategies)}"
        
        # Create multiple strategies to test within-test operations
        for i in range(3):
            create_response = authenticated_client.post(
                "/strategies/",
                json={
                    "name": f"Strategy {i+1}", 
                    "description": f"Test strategy {i+1}", 
                    "holdings": [{"symbol": "AAPL", "target_weight": 1.0}]
                },
            )
            assert create_response.status_code == 200
        
        # Verify we have exactly 3 strategies
        response = authenticated_client.get("/strategies/")
        assert response.status_code == 200
        strategies = response.json()
        assert len(strategies) == 3, f"Test 3: Expected 3 strategies, found {len(strategies)}"
    
    def test_isolation_4_database_transactions(self, authenticated_client, test_db_session):
        """Test that database transactions work properly with isolation."""
        from services.app.database import Strategy, User
        
        # Check database directly - should be empty
        db_strategies = test_db_session.query(Strategy).all()
        assert len(db_strategies) == 0, f"Expected 0 strategies in DB, found {len(db_strategies)}"
        
        # Create strategy via API
        create_response = authenticated_client.post(
            "/strategies/",
            json={
                "name": "DB Test Strategy", 
                "description": "Testing DB isolation", 
                "holdings": [{"symbol": "AAPL", "target_weight": 1.0}]
            },
        )
        assert create_response.status_code == 200
        
        # Check database directly - should now have 1 strategy
        test_db_session.commit()  # Ensure changes are visible
        db_strategies = test_db_session.query(Strategy).all()
        assert len(db_strategies) == 1, f"Expected 1 strategy in DB after creation, found {len(db_strategies)}"
        assert db_strategies[0].name == "DB Test Strategy"
        
        # Verify via API as well
        response = authenticated_client.get("/strategies/")
        assert response.status_code == 200
        strategies = response.json()
        assert len(strategies) == 1, f"Expected 1 strategy via API, found {len(strategies)}"
    
    def test_isolation_5_user_isolation(self, authenticated_client, test_user, test_db_session):
        """Test that user data is properly isolated between tests."""
        from services.app.database import User
        
        # Should have exactly one test user
        db_users = test_db_session.query(User).all()
        assert len(db_users) == 1, f"Expected 1 user in DB, found {len(db_users)}"
        assert db_users[0].email == test_user.email
        
        # User should have no strategies initially
        response = authenticated_client.get("/strategies/")
        assert response.status_code == 200
        strategies = response.json()
        assert len(strategies) == 0, f"Expected 0 strategies for test user, found {len(strategies)}"
        
        # Create a strategy for this user
        create_response = authenticated_client.post(
            "/strategies/",
            json={
                "name": "User Test Strategy", 
                "description": "Testing user isolation", 
                "holdings": [{"symbol": "AAPL", "target_weight": 1.0}]
            },
        )
        assert create_response.status_code == 200
        
        # Verify strategy belongs to the test user
        response = authenticated_client.get("/strategies/")
        assert response.status_code == 200
        strategies = response.json()
        assert len(strategies) == 1
        
        # Check in database
        from services.app.database import Strategy
        db_strategies = test_db_session.query(Strategy).all()
        assert len(db_strategies) == 1
        assert db_strategies[0].user_id == test_user.id


def test_run_all_isolation_tests():
    """Meta-test to ensure all isolation tests can run together."""
    # This test just documents that the above tests should all pass
    # when run together, demonstrating proper isolation
    pass