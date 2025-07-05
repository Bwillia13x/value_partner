"""Pytest configuration to ensure project root is importable and testing env is set."""
from __future__ import annotations

import sys
from pathlib import Path
import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# Add project root to Python path so that `import services` works regardless of
# where pytest is invoked from.
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Ensure we are in testing mode so parts of the codebase can disable expensive
# dependencies (e.g. bcrypt, Celery workers) and bypass security checks where
# appropriate.
os.environ.setdefault("TESTING", "1")

# Load environment variables defined in services/.env for tests
from dotenv import load_dotenv  # type: ignore
load_dotenv(dotenv_path=ROOT_DIR / "services" / ".env", override=False)

# Import after environment setup
from services.app.main import app
from services.app.database import Base, get_db
from services.app import crud, auth, schemas

# Use in-memory SQLite for complete isolation
TEST_DATABASE_URL = "sqlite+pysqlite:///file::memory:?cache=shared&uri=true"

@pytest.fixture(scope="function")
def test_engine():
    """Create a fresh in-memory database engine for each test."""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False  # Set to True for SQL debugging
    )
    # Create all tables
    Base.metadata.create_all(bind=engine)
    yield engine
    # Clean up
    Base.metadata.drop_all(bind=engine)
    engine.dispose()

@pytest.fixture(scope="function")
def test_db_session(test_engine):
    """Create a fresh database session for each test with automatic rollback."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    
    # Create a connection and transaction
    connection = test_engine.connect()
    transaction = connection.begin()
    
    # Create session bound to the connection
    session = TestingSessionLocal(bind=connection)
    
    try:
        yield session
    finally:
        session.close()
        # Rollback the transaction to ensure complete isolation
        transaction.rollback()
        connection.close()

@pytest.fixture(scope="function")
def test_client(test_db_session):
    """Create a test client with isolated database session."""
    # Override the get_db dependency to use our test session
    def override_get_db():
        try:
            yield test_db_session
        finally:
            pass  # Session cleanup handled by test_db_session fixture
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as client:
        yield client
    
    # Clean up dependency overrides
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
def test_user(test_db_session):
    """Create a test user for authentication tests."""
    user_data = schemas.UserCreate(
        email="test@example.com", 
        password="testpassword", 
        name="Test User"
    )
    hashed_password = auth.get_password_hash(user_data.password)
    user = crud.create_user(test_db_session, user=user_data, hashed_password=hashed_password)
    test_db_session.commit()
    test_db_session.refresh(user)
    return user

@pytest.fixture(scope="function")
def auth_headers(test_client, test_user):
    """Get authentication headers for a test user."""
    # Get access token
    token_response = test_client.post(
        "/auth/token",
        data={
            "username": test_user.email,
            "password": "testpassword"
        }
    )
    assert token_response.status_code == 200, f"Token request failed: {token_response.text}"
    
    access_token = token_response.json()["access_token"]
    return {"Authorization": f"Bearer {access_token}"}

@pytest.fixture(scope="function")
def authenticated_client(test_client, auth_headers):
    """Create an authenticated test client."""
    # Add headers to the client
    test_client.headers.update(auth_headers)
    return test_client
