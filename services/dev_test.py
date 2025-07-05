#!/usr/bin/env python3
"""
Development test script to verify basic functionality
"""

import os
import sys
import asyncio
from pathlib import Path

# Add the app directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.database import get_db, init_db

def test_basic_features():
    """Test basic functionality without requiring external services"""
    print("🚀 Value Partner Development Test Suite")
    print("=" * 50)
    
    # Test 1: Database Connection
    print("\n1. Testing Database Connection...")
    try:
        # Initialize database
        init_db()
        
        # Test database connection
        db = next(get_db())
        from sqlalchemy import text
        result = db.execute(text("SELECT 1 as test")).fetchone()
        if result and result[0] == 1:
            print("✅ Database connection successful")
        else:
            print("❌ Database connection failed")
            return False
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False
    
    # Test 2: API Health Check
    print("\n2. Testing API Health...")
    try:
        import requests
        response = requests.get("http://127.0.0.1:8000/health", timeout=5)
        if response.status_code == 200:
            print("✅ API health check successful")
        else:
            print(f"❌ API health check failed: {response.status_code}")
    except Exception as e:
        print(f"❌ API health check failed: {e}")
        print("   Make sure the backend is running: python3 -m uvicorn app.main:app --reload")
    
    # Test 3: Create Test User and Account
    print("\n3. Testing User and Account Creation...")
    try:
        from app.crud import create_user, create_account_entry
        from app.schemas import UserCreate, AccountCreate
        
        db = next(get_db())
        
        # Create test user
        user_data = UserCreate(
            email="test@example.com",
            username="testuser",
            full_name="Test User"
        )
        test_user = create_user(db, user_data)
        print(f"✅ Test user created: ID {test_user.id}")
        
        # Create test account
        account_data = AccountCreate(
            name="Test Investment Account",
            account_type="investment",
            account_subtype="investment",
            is_manual=True
        )
        test_account = create_account_entry(db, account_data, test_user.id)
        print(f"✅ Test account created: ID {test_account.id}")
        
        # Test account retrieval
        from app.crud import get_user_accounts
        accounts = get_user_accounts(db, test_user.id)
        print(f"✅ Account retrieval successful: {len(accounts)} accounts found")
        
    except Exception as e:
        print(f"❌ User/Account creation failed: {e}")
    
    # Test 4: Frontend Connection
    print("\n4. Testing Frontend Connection...")
    try:
        import requests
        response = requests.get("http://127.0.0.1:3000", timeout=5)
        if response.status_code == 200:
            print("✅ Frontend connection successful")
        else:
            print(f"❌ Frontend connection failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Frontend connection failed: {e}")
        print("   Make sure the frontend is running: npm run dev")
    
    print("\n" + "=" * 50)
    print("🎯 Quick Setup Guide for Testing:")
    print("1. Backend: cd services && python3 -m uvicorn app.main:app --reload")
    print("2. Frontend: cd frontend && npm run dev")
    print("3. Visit: http://localhost:3000")
    print("4. Test Plaid: Use sandbox credentials (no real bank connection)")
    print("\n📝 Features you can test:")
    print("- Portfolio dashboard navigation")
    print("- Plaid Link integration (sandbox mode)")
    print("- Real-time data updates")
    print("- Account management")
    print("- Investment tracking")
    
    return True

if __name__ == "__main__":
    test_basic_features()