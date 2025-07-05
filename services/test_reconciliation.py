#!/usr/bin/env python3
"""
Test script for the Celery reconciliation tasks.

This script tests the end-to-end reconciliation flow by:
1. Creating a test account in the database
2. Triggering the reconciliation task
3. Verifying the results
"""
import os
import sys
from datetime import datetime
from sqlalchemy.orm import Session
from unittest.mock import patch, MagicMock

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

os.environ['PLAID_CLIENT_ID'] = 'test_client_id'
os.environ['PLAID_SECRET'] = 'test_secret'

from app.database import get_db, init_db, Account, User
from app.tasks.reconciliation import reconcile_account, reconcile_all_accounts

def create_test_account(db: Session):
    """Create a test account for reconciliation testing"""
    # Create a test user if it doesn't exist
    user = db.query(User).filter(User.email == "test@example.com").first()
    if not user:
        user = User(
            email="test@example.com",
            hashed_password="$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW",  # "secret"
            name="Test User"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # Create a test account
    account = Account(
        user_id=user.id,
        name="Test Investment Account",
        account_type="investment",
        plaid_account_id="test-account-123",
        plaid_item_id="test-item-123",
        plaid_access_token="test-access-token-123",
        current_balance=10000.00,
        is_active=True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    
    print(f"Created test account with ID: {account.id}")
    return account

@patch('app.integrations.get_plaid_service')
def test_reconcile_account(mock_get_plaid_service):
    mock_plaid_service = MagicMock()
    mock_get_plaid_service.return_value = mock_plaid_service
    """Test reconciling a single account"""
    # Configure the mock PlaidService
    mock_plaid_service.get_accounts.return_value = [
        {
            "account_id": "test-account-123",
            "name": "Test Investment Account",
            "official_name": "Test Official Name",
            "type": "investment",
            "subtype": "brokerage",
            "mask": "1234",
            "balances": {
                "available": 10000.00,
                "current": 10000.00,
                "iso_currency_code": "USD",
                "unofficial_currency_code": None
            }
        }
    ]
    mock_plaid_service.get_investment_holdings.return_value = [
        {
            "account_id": "test-account-123",
            "security_id": "test-security-456",
            "ticker_symbol": "TSLA",
            "name": "Tesla Inc.",
            "type": "equity",
            "quantity": 10.0,
            "cost_basis": 5000.00,
            "institution_price": 500.00,
            "institution_value": 5000.00,
            "iso_currency_code": "USD",
            "unofficial_currency_code": None
        }
    ]

    db = next(get_db())
    try:
        # Create a test account
        account = create_test_account(db)
        
        # Call the task directly (synchronously for testing)
        print(f"Testing reconciliation for account {account.id}...")
        result = reconcile_account(account.id, account.user_id)
        
        print("Reconciliation result:", result)
        
        # Verify the account was updated
        updated_account = db.query(Account).filter(Account.id == account.id).first()
        print(f"Account balance after reconciliation: {updated_account.current_balance}")
        
        # Assertions to verify the mock was called and data was processed
        mock_plaid_service.get_accounts.assert_called_once()
        mock_plaid_service.get_investment_holdings.assert_called_once()
        assert result["status"] == "success"
        assert updated_account.current_balance == 10000.00 # Assuming no change in balance from mock
        
        return result
    except Exception as e:
        print(f"Error in test_reconcile_account: {e}", file=sys.stderr)
        raise
    finally:
        db.close()

@patch('app.integrations.get_plaid_service')
@patch.dict(os.environ, {'PLAID_CLIENT_ID': 'test_client_id', 'PLAID_SECRET': 'test_secret'})
def test_reconcile_all_accounts(mock_get_plaid_service):
    mock_plaid_service = MagicMock()
    mock_get_plaid_service.return_value = mock_plaid_service
    """Test the reconcile_all_accounts task"""
    # Configure the mock PlaidService
    mock_plaid_service.get_accounts.return_value = [
        {
            "account_id": "test-account-123",
            "name": "Test Investment Account",
            "official_name": "Test Official Name",
            "type": "investment",
            "subtype": "brokerage",
            "mask": "1234",
            "balances": {
                "available": 10000.00,
                "current": 10000.00,
                "iso_currency_code": "USD",
                "unofficial_currency_code": None
            }
        }
    ]
    mock_plaid_service.get_investment_holdings.return_value = [
        {
            "account_id": "test-account-123",
            "security_id": "test-security-456",
            "ticker_symbol": "TSLA",
            "name": "Tesla Inc.",
            "type": "equity",
            "quantity": 10.0,
            "cost_basis": 5000.00,
            "institution_price": 500.00,
            "institution_value": 5000.00,
            "iso_currency_code": "USD",
            "unofficial_currency_code": None
        }
    ]

    db = next(get_db())
    try:
        # Ensure we have at least one account
        if db.query(Account).count() == 0:
            create_test_account(db)
        
        # Call the task directly (synchronously for testing)
        print("Testing reconcile_all_accounts...")
        result = reconcile_all_accounts.apply()
        
        print("Reconcile all accounts result:", result)
        
        # Assertions to verify the mock was called and data was processed
        mock_plaid_service.get_accounts.assert_called_once()
        mock_plaid_service.get_investment_holdings.assert_called_once()
        assert result["status"] == "success"
        
        return result
    except Exception as e:
        print(f"Error in test_reconcile_all_accounts: {e}", file=sys.stderr)
        raise
    finally:
        db.close()

if __name__ == "__main__":
    # Initialize the database
    init_db()
    
    # Run the tests
    print("=== Starting reconciliation tests ===")
    
    print("\n--- Testing single account reconciliation ---")
    test_reconcile_account()
    
    print("\n--- Testing reconcile all accounts ---")
    test_reconcile_all_accounts()
    
    print("\n=== Reconciliation tests completed ===")
