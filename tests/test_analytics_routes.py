import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from unittest.mock import MagicMock, patch

from services.app.database import User
from services.app.analytics_routes import PerformanceResponse # Import other response models as needed
from services.app.analytics import PortfolioAnalytics # To mock its methods

# Test GET /performance/{user_id}
def test_get_portfolio_performance_success(authenticated_client: TestClient, test_user: User, mocker):
    # Mock the PortfolioAnalytics instance and its method
    mock_analytics_instance = MagicMock(spec=PortfolioAnalytics)
    mock_analytics_instance.calculate_performance_metrics.return_value = MagicMock(
        total_return=0.15,
        annualized_return=0.18,
        volatility=0.22,
        sharpe_ratio=0.8,
        max_drawdown=-0.10,
        current_value=115000.0,
        benchmark_return=0.12,
        alpha=0.03,
        beta=1.1
    )

    # Patch the constructor of PortfolioAnalytics to return our mock instance
    mocker.patch("services.app.analytics_routes.PortfolioAnalytics", return_value=mock_analytics_instance)

    response = authenticated_client.get(f"/analytics/performance/{test_user.id}?period_days=180")

    assert response.status_code == 200
    data = response.json()
    assert data["total_return"] == 0.15
    assert data["sharpe_ratio"] == 0.8
    assert data["current_value"] == 115000.0

    # Verify the mocked method was called correctly
    mock_analytics_instance.calculate_performance_metrics.assert_called_once_with(test_user.id, 180)

def test_get_portfolio_performance_default_period(authenticated_client: TestClient, test_user: User, mocker):
    mock_analytics_instance = MagicMock(spec=PortfolioAnalytics)
    mock_analytics_instance.calculate_performance_metrics.return_value = MagicMock(total_return=0.10) # Only need one field for this check
    mocker.patch("services.app.analytics_routes.PortfolioAnalytics", return_value=mock_analytics_instance)

    response = authenticated_client.get(f"/analytics/performance/{test_user.id}") # No period_days query param

    assert response.status_code == 200
    # Verify the mocked method was called with the default period_days (365)
    mock_analytics_instance.calculate_performance_metrics.assert_called_once_with(test_user.id, 365)


def test_get_portfolio_performance_data_not_found(authenticated_client: TestClient, test_user: User, mocker):
    mock_analytics_instance = MagicMock(spec=PortfolioAnalytics)
    mock_analytics_instance.calculate_performance_metrics.return_value = None # Simulate no data
    mocker.patch("services.app.analytics_routes.PortfolioAnalytics", return_value=mock_analytics_instance)

    response = authenticated_client.get(f"/analytics/performance/{test_user.id}")

    assert response.status_code == 404
    assert response.json()["detail"] == "No performance data found"

def test_get_portfolio_performance_unauthenticated(test_client: TestClient, test_user: User):
    # test_user is passed here just to have a user_id for the URL, client is unauthenticated
    response = test_client.get(f"/analytics/performance/{test_user.id}")
    assert response.status_code == 401 # Expecting 401 due to Depends(get_current_user)

# Note: The analytics_routes.py uses `user_id: int` in the path, and then checks `user_id != current_user.id`.
# This means a user could try to access /analytics/performance/OTHER_USER_ID.
# The check `if user_id != current_user.id: raise HTTPException(status_code=status.HTTP_403_FORBIDDEN...` handles this.
# The `authenticated_client` fixture uses `test_user.id` by default.
# Let's add a test for this specific 403 case.

def test_get_portfolio_performance_forbidden(authenticated_client: TestClient, test_user: User, test_db_session: Session):
    # test_user is user 1 (typically, from fixture)
    # Create another user
    from tests.test_portfolio_routes import create_test_user # Helper from other test file
    other_user = create_test_user(test_db_session, id=test_user.id + 1, email="other@example.com", name="Other User")

    # authenticated_client is for test_user. Try to access other_user's data.
    response = authenticated_client.get(f"/analytics/performance/{other_user.id}")
    assert response.status_code == 403
    assert response.json()["detail"] == "Access denied"


# Placeholder for other analytics endpoints tests
# Test GET /performance/{user_id}/timeseries
# Test GET /allocation/{user_id}
# Test GET /attribution/{user_id}
# Test GET /summary/{user_id}
# Test GET /benchmarks (this one is not user-specific)
# Test GET /risk-metrics/{user_id}

def test_get_benchmarks(authenticated_client: TestClient): # Can also use test_client if it's truly public
    response = authenticated_client.get("/analytics/benchmarks")
    assert response.status_code == 200
    data = response.json()
    assert "benchmarks" in data
    assert isinstance(data["benchmarks"], list)
    assert len(data["benchmarks"]) > 0
    assert "symbol" in data["benchmarks"][0]
    assert "name" in data["benchmarks"][0]

# Test GET /performance/{user_id}/timeseries
def test_get_portfolio_timeseries_success(authenticated_client: TestClient, test_user: User, mocker):
    mock_analytics_instance = MagicMock(spec=PortfolioAnalytics)
    # Mocking a pandas DataFrame like structure for the return
    mock_df_data = {
        'date': [datetime(2023, 1, 1), datetime(2023, 1, 2)],
        'portfolio_value': [10000.0, 10100.0],
        'daily_return': [0.0, 0.01]
    }
    # Create a MagicMock that mimics a DataFrame for tolist() and strftime
    mock_df = MagicMock()
    mock_df.__getitem__.side_effect = lambda key: MagicMock(tolist=lambda: mock_df_data[key], # Pandas Series have tolist
                                                            dt=MagicMock(strftime=lambda fmt: [d.strftime(fmt) for d in mock_df_data['date']]))
                                                            # Mocking series.dt.strftime
    mock_df.empty = False # Simulate non-empty DataFrame

    # A bit complex mocking for DataFrame, simpler way:
    # Have calculate_portfolio_returns return a list of dicts or a simpler structure if internal df usage is not heavy
    # For now, assuming the route extracts lists like: dates=[d.strftime("%Y-%m-%d") for d in returns_df['date']]
    # Let's simplify the mock for what the route needs.
    # The route does: returns_df['date'], returns_df['portfolio_value'].tolist(), returns_df['daily_return'].fillna(0).tolist()

    # Simplified mock:
    mock_returns_df_like_object = MagicMock()
    mock_returns_df_like_object.empty = False
    # Directly provide what .tolist() and strftime would produce
    mock_returns_df_like_object.__getitem__.side_effect = lambda key: {
        'date': [datetime(2023,1,1), datetime(2023,1,2)], # This will be transformed by strftime in the route
        'portfolio_value': [10000.0, 10100.0],
        'daily_return': [0.0, 0.01]
    }[key]


    mock_analytics_instance.calculate_portfolio_returns.return_value = mock_returns_df_like_object
    mocker.patch("services.app.analytics_routes.PortfolioAnalytics", return_value=mock_analytics_instance)

    response = authenticated_client.get(f"/analytics/performance/{test_user.id}/timeseries?period_days=30")
    assert response.status_code == 200
    data = response.json()
    assert data["dates"] == ["2023-01-01", "2023-01-02"]
    assert data["portfolio_values"] == [10000.0, 10100.0]
    assert data["daily_returns"] == [0.0, 0.01]

    # Check call_args for calculate_portfolio_returns (start_date, end_date)
    # This requires knowing how start_date/end_date are computed in the route or mocking datetime.now()
    # For now, just assert it was called. A more precise check would involve datetime mocking.
    mock_analytics_instance.calculate_portfolio_returns.assert_called_once()
    # args, _ = mock_analytics_instance.calculate_portfolio_returns.call_args
    # assert args[0] == test_user.id
    # assert isinstance(args[1], datetime) # start_date
    # assert isinstance(args[2], datetime) # end_date


def test_get_portfolio_timeseries_empty(authenticated_client: TestClient, test_user: User, mocker):
    mock_analytics_instance = MagicMock(spec=PortfolioAnalytics)
    mock_empty_df = MagicMock()
    mock_empty_df.empty = True
    mock_analytics_instance.calculate_portfolio_returns.return_value = mock_empty_df
    mocker.patch("services.app.analytics_routes.PortfolioAnalytics", return_value=mock_analytics_instance)

    response = authenticated_client.get(f"/analytics/performance/{test_user.id}/timeseries")
    assert response.status_code == 404
    assert response.json()["detail"] == "No time series data found"

# Test GET /allocation/{user_id}
def test_get_asset_allocation_success(authenticated_client: TestClient, test_user: User, mocker):
    mock_analytics_instance = MagicMock(spec=PortfolioAnalytics)
    mock_analytics_instance.get_asset_allocation.return_value = {"Equity": 0.6, "Bond": 0.3, "Cash": 0.1}
    mock_analytics_instance.get_current_portfolio_value.return_value = 120000.0
    mocker.patch("services.app.analytics_routes.PortfolioAnalytics", return_value=mock_analytics_instance)

    response = authenticated_client.get(f"/analytics/allocation/{test_user.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["allocation"] == {"Equity": 0.6, "Bond": 0.3, "Cash": 0.1}
    assert data["total_value"] == 120000.0
    mock_analytics_instance.get_asset_allocation.assert_called_once_with(test_user.id)
    mock_analytics_instance.get_current_portfolio_value.assert_called_once_with(test_user.id)

# Test GET /attribution/{user_id}
def test_get_performance_attribution_success(authenticated_client: TestClient, test_user: User, mocker):
    mock_analytics_instance = MagicMock(spec=PortfolioAnalytics)
    mock_analytics_instance.get_performance_attribution.return_value = {"AAPL": 0.05, "MSFT": 0.03, "GOOG": -0.01}
    mocker.patch("services.app.analytics_routes.PortfolioAnalytics", return_value=mock_analytics_instance)

    response = authenticated_client.get(f"/analytics/attribution/{test_user.id}?period_days=90")
    assert response.status_code == 200
    data = response.json()
    assert data["contributions"] == {"AAPL": 0.05, "MSFT": 0.03, "GOOG": -0.01}
    mock_analytics_instance.get_performance_attribution.assert_called_once_with(test_user.id, 90)

# Test GET /summary/{user_id}
def test_get_analytics_summary_success(authenticated_client: TestClient, test_user: User, mocker):
    mock_analytics_instance = MagicMock(spec=PortfolioAnalytics)
    mock_perf_metrics = MagicMock(total_return=0.1) # Mocking a simple object with __dict__
    mock_perf_metrics.__dict__ = {"total_return": 0.1, "sharpe_ratio": 0.7}

    mock_analytics_instance.calculate_performance_metrics.return_value = mock_perf_metrics
    mock_analytics_instance.get_asset_allocation.return_value = {"Equity": 0.7, "Cash": 0.3}
    mock_analytics_instance.get_performance_attribution.return_value = {"TSLA": 0.08}
    mocker.patch("services.app.analytics_routes.PortfolioAnalytics", return_value=mock_analytics_instance)

    response = authenticated_client.get(f"/analytics/summary/{test_user.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["performance"] == {"total_return": 0.1, "sharpe_ratio": 0.7}
    assert data["allocation"] == {"Equity": 0.7, "Cash": 0.3}
    assert data["attribution"] == {"TSLA": 0.08}
    assert "updated_at" in data

    mock_analytics_instance.calculate_performance_metrics.assert_called_once_with(test_user.id) # Default period_days
    mock_analytics_instance.get_asset_allocation.assert_called_once_with(test_user.id)
    mock_analytics_instance.get_performance_attribution.assert_called_once_with(test_user.id) # Default period_days

# Test GET /risk-metrics/{user_id}
def test_get_risk_metrics_success(authenticated_client: TestClient, test_user: User, mocker):
    mock_analytics_instance = MagicMock(spec=PortfolioAnalytics)
    # Mocking a pandas Series like structure for returns
    mock_returns_series = MagicMock()
    mock_returns_series.quantile.side_effect = lambda q: -0.05 if q == 0.05 else -0.08 # VaR 95 / 99
    mock_returns_series.__le__.return_value = mock_returns_series # For boolean indexing
    mock_returns_series.mean.return_value = -0.06 # Expected shortfall
    mock_returns_series.skew.return_value = -0.5
    mock_returns_series.kurtosis.return_value = 3.5
    mock_returns_series.dropna.return_value = mock_returns_series # simulate dropna returning the series

    mock_df_like_object = MagicMock()
    mock_df_like_object.empty = False
    mock_df_like_object.__getitem__.return_value = mock_returns_series # For returns_df['daily_return']

    mock_analytics_instance.calculate_portfolio_returns.return_value = mock_df_like_object
    mocker.patch("services.app.analytics_routes.PortfolioAnalytics", return_value=mock_analytics_instance)

    response = authenticated_client.get(f"/analytics/risk-metrics/{test_user.id}?period_days=180")
    assert response.status_code == 200
    data = response.json()
    assert data["value_at_risk"]["var_95"] == -0.05
    assert data["value_at_risk"]["var_99"] == -0.08 # Based on side_effect logic
    assert data["distribution_metrics"]["skewness"] == -0.5
    assert data["period_days"] == 180
    assert "updated_at" in data

    mock_analytics_instance.calculate_portfolio_returns.assert_called_once()
    # args, _ = mock_analytics_instance.calculate_portfolio_returns.call_args
    # assert args[0] == test_user.id # First arg is user_id


def test_get_risk_metrics_empty_data(authenticated_client: TestClient, test_user: User, mocker):
    mock_analytics_instance = MagicMock(spec=PortfolioAnalytics)
    mock_empty_df = MagicMock()
    mock_empty_df.empty = True
    mock_analytics_instance.calculate_portfolio_returns.return_value = mock_empty_df
    mocker.patch("services.app.analytics_routes.PortfolioAnalytics", return_value=mock_analytics_instance)

    response = authenticated_client.get(f"/analytics/risk-metrics/{test_user.id}")
    assert response.status_code == 404
    assert response.json()["detail"] == "No data available for risk analysis"

# Final TODOs for this file:
# 1. Add tests for different query parameters (e.g., `period_days` for attribution if not covered).
# 2. Consider testing specific error conditions from PortfolioAnalytics if they should result in different API responses.
# 3. Write dedicated unit tests for the PortfolioAnalytics class itself.
# 4. The current_user dependency has been updated to use `get_current_active_user` from `services.app.auth`.
#    The tests for 401 (unauthenticated) and 403 (forbidden) should correctly cover these scenarios.
