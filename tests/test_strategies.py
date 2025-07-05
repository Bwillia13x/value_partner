from dotenv import load_dotenv
load_dotenv(dotenv_path='services/.env')

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from services.app.main import app
from services.app.database import Base, get_db
from services.app import crud, auth, schemas, auth_routes
import pytest

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)

def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db



@pytest.fixture(scope="function")
def db_session():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(scope="function")
def authenticated_client(db_session):
    app.dependency_overrides.update({get_db: lambda: db_session})
    test_client = TestClient(app)

    # Create a test user
    user_data = schemas.UserCreate(email="test@example.com", password="testpassword", name="Test User")
    hashed_password = auth.get_password_hash(user_data.password)
    user = crud.create_user(db_session, user=user_data, hashed_password=hashed_password)
    db_session.flush()
    db_session.refresh(user)

    # Obtain an access token
    token_response = test_client.post(
        "/auth/token",
        data={
            "username": user.email,
            "password": user_data.password
        }
    )
    access_token = token_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    yield TestClient(app, headers=headers)
    app.dependency_overrides.clear()

def test_create_strategy(authenticated_client):
    response = authenticated_client.post(
        "/strategies/",
        json={"name": "Growth", "description": "Growth strategy", "holdings": [{"symbol": "AAPL", "target_weight": 0.5}, {"symbol": "GOOG", "target_weight": 0.5}]},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["name"] == "Growth"
    assert len(data["holdings"]) == 2
    assert data["holdings"][0]["symbol"] == "AAPL"
    assert data["holdings"][1]["symbol"] == "GOOG"

def test_read_strategies(authenticated_client):
    authenticated_client.post(
        "/strategies/",
        json={"name": "Growth", "description": "Growth strategy", "holdings": [{"symbol": "AAPL", "target_weight": 0.5}, {"symbol": "GOOG", "target_weight": 0.5}]},
    )
    response = authenticated_client.get("/strategies/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "Growth"

def test_rebalance_strategy(authenticated_client):
    # Create a strategy
    strategy_response = authenticated_client.post(
        "/strategies/",
        json={"name": "Value", "description": "Value strategy", "holdings": [{"symbol": "MSFT", "target_weight": 1.0}]},
    )
    strategy_id = strategy_response.json()["id"]

    # In a real test, you would add some holdings to the test database here

    response = authenticated_client.post(f"/strategies/{strategy_id}/rebalance")
    assert response.status_code == 200
    data = response.json()
    assert "proposed_trades" in data
    assert "executed_trades" in data