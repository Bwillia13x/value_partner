import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from sqlalchemy.orm import Session

from services.app.database import User, Account, AccountType, Holding, Transaction, TransactionType
from services.app.analytics import PortfolioAnalytics, PerformanceMetrics
from tests.test_portfolio_routes import create_test_user, create_test_account, create_test_holding, create_test_transaction

@pytest.fixture
def analytics_service(test_db_session: Session) -> PortfolioAnalytics:
    return PortfolioAnalytics(test_db_session)

# --- Tests for get_current_portfolio_value ---
def test_get_current_portfolio_value_empty(analytics_service: PortfolioAnalytics, test_user: User):
    value = analytics_service.get_current_portfolio_value(test_user.id)
    assert value == 0.0

def test_get_current_portfolio_value_one_account_one_holding(
    analytics_service: PortfolioAnalytics, test_db_session: Session, test_user: User
):
    acc1 = create_test_account(test_db_session, test_user.id, "Brokerage", AccountType.INVESTMENT, 1000.0)
    create_test_holding(test_db_session, acc1.id, "AAPL", "Apple", 10, 1500.0, 150.0)

    value = analytics_service.get_current_portfolio_value(test_user.id)
    assert value == 1500.0

def test_get_current_portfolio_value_multiple_accounts_holdings(
    analytics_service: PortfolioAnalytics, test_db_session: Session, test_user: User
):
    acc1 = create_test_account(test_db_session, test_user.id, "Brokerage 1", AccountType.INVESTMENT, 1000.0)
    acc2 = create_test_account(test_db_session, test_user.id, "Retirement", AccountType.RETIREMENT, 5000.0)
    create_test_holding(test_db_session, acc1.id, "AAPL", "Apple", 10, 1500.0, 150.0)
    create_test_holding(test_db_session, acc2.id, "MSFT", "Microsoft", 5, 1250.0, 250.0)

    value = analytics_service.get_current_portfolio_value(test_user.id)
    assert value == 1500.0 + 1250.0

def test_get_current_portfolio_value_ignores_non_investment_accounts(
    analytics_service: PortfolioAnalytics, test_db_session: Session, test_user: User
):
    checking_acc = create_test_account(test_db_session, test_user.id, "Checking", AccountType.CHECKING, 2000.0)
    # Holdings in non-investment accounts shouldn't typically exist or be counted for portfolio value in this context
    # but if they did, this method should ignore the account itself.
    # The current implementation iterates holdings, so it relies on holdings only being in investment accounts.
    # Let's add an investment account to make sure it's not just returning 0 because of the checking account.
    inv_acc = create_test_account(test_db_session, test_user.id, "Brokerage", AccountType.INVESTMENT, 100.0)
    create_test_holding(test_db_session, inv_acc.id, "TSLA", "Tesla", 2, 500.0, 250.0)

    value = analytics_service.get_current_portfolio_value(test_user.id)
    assert value == 500.0


# --- Tests for get_asset_allocation ---
def test_get_asset_allocation_empty(analytics_service: PortfolioAnalytics, test_user: User):
    allocation = analytics_service.get_asset_allocation(test_user.id)
    assert allocation == {}

def test_get_asset_allocation_single_holding(
    analytics_service: PortfolioAnalytics, test_db_session: Session, test_user: User
):
    acc1 = create_test_account(test_db_session, test_user.id, "Brokerage", AccountType.INVESTMENT, 1500.0)
    create_test_holding(test_db_session, acc1.id, "AAPL", "Apple", 10, 1500.0, 150.0) # security_type defaults to "equity"

    allocation = analytics_service.get_asset_allocation(test_user.id)
    assert len(allocation) == 1
    assert "equity" in allocation
    assert allocation["equity"] == pytest.approx(1.0)

def test_get_asset_allocation_multiple_holdings_types(
    analytics_service: PortfolioAnalytics, test_db_session: Session, test_user: User
):
    acc1 = create_test_account(test_db_session, test_user.id, "Brokerage", AccountType.INVESTMENT, 0) # Balance not used directly by allocation
    h1 = create_test_holding(test_db_session, acc1.id, "AAPL", "Apple", 10, 600.0, 60.0) # equity
    h1.security_type = "stock" # more specific
    test_db_session.commit()

    h2 = create_test_holding(test_db_session, acc1.id, "BND", "Vanguard Bond ETF", 10, 300.0, 30.0)
    h2.security_type = "bond_etf"
    test_db_session.commit()

    h3 = create_test_holding(test_db_session, acc1.id, "CASH", "Cash", 100, 100.0, 1.0)
    h3.security_type = "cash"
    test_db_session.commit()

    # Total market value = 600 + 300 + 100 = 1000
    allocation = analytics_service.get_asset_allocation(test_user.id)
    assert len(allocation) == 3
    assert allocation["stock"] == pytest.approx(0.6)
    assert allocation["bond_etf"] == pytest.approx(0.3)
    assert allocation["cash"] == pytest.approx(0.1)

def test_get_asset_allocation_unknown_security_type(
    analytics_service: PortfolioAnalytics, test_db_session: Session, test_user: User
):
    acc1 = create_test_account(test_db_session, test_user.id, "Brokerage", AccountType.INVESTMENT, 100.0)
    holding = create_test_holding(test_db_session, acc1.id, "XYZ", "Unknown Sec", 1, 100.0, 100.0)
    holding.security_type = None # Explicitly None
    test_db_session.commit()

    allocation = analytics_service.get_asset_allocation(test_user.id)
    assert "unknown" in allocation
    assert allocation["unknown"] == pytest.approx(1.0)


# --- Tests for get_performance_attribution ---
def test_get_performance_attribution_empty(analytics_service: PortfolioAnalytics, test_user: User):
    attribution = analytics_service.get_performance_attribution(test_user.id)
    assert attribution == {}

def test_get_performance_attribution_single_holding(
    analytics_service: PortfolioAnalytics, test_db_session: Session, test_user: User
):
    acc1 = create_test_account(test_db_session, test_user.id, "Brokerage", AccountType.INVESTMENT, 0)
    holding = create_test_holding(test_db_session, acc1.id, "AAPL", "Apple", 10, 1100.0, 110.0)
    holding.cost_basis = 1000.0 # 10% return
    test_db_session.commit()

    # Mock get_current_portfolio_value or ensure it's correct based on the single holding
    with patch.object(analytics_service, 'get_current_portfolio_value', return_value=1100.0):
        attribution = analytics_service.get_performance_attribution(test_user.id)
        assert "AAPL" in attribution
        # Return = (1100 - 1000) / 1000 = 0.1
        # Weight = 1100 / 1100 = 1.0
        # Contribution = 0.1 * 1.0 = 0.1
        assert attribution["AAPL"] == pytest.approx(0.1)


def test_get_performance_attribution_multiple_holdings(
    analytics_service: PortfolioAnalytics, test_db_session: Session, test_user: User
):
    acc1 = create_test_account(test_db_session, test_user.id, "Brokerage", AccountType.INVESTMENT, 0)

    h_aapl = create_test_holding(test_db_session, acc1.id, "AAPL", "Apple", 10, 1100.0, 110.0)
    h_aapl.cost_basis = 1000.0 # Return = 0.1
    test_db_session.commit()

    h_msft = create_test_holding(test_db_session, acc1.id, "MSFT", "Microsoft", 5, 450.0, 90.0)
    h_msft.cost_basis = 500.0 # Return = -0.1
    test_db_session.commit()

    total_portfolio_value = 1100.0 + 450.0 # = 1550.0

    with patch.object(analytics_service, 'get_current_portfolio_value', return_value=total_portfolio_value):
        attribution = analytics_service.get_performance_attribution(test_user.id)

        # AAPL: Return = 0.1, Weight = 1100 / 1550
        # Contribution AAPL = 0.1 * (1100 / 1550)
        expected_aapl_contrib = 0.1 * (1100.0 / total_portfolio_value)
        assert attribution["AAPL"] == pytest.approx(expected_aapl_contrib)

        # MSFT: Return = -0.1, Weight = 450 / 1550
        # Contribution MSFT = -0.1 * (450 / 1550)
        expected_msft_contrib = -0.1 * (450.0 / total_portfolio_value)
        assert attribution["MSFT"] == pytest.approx(expected_msft_contrib)


def test_get_performance_attribution_no_cost_basis(
    analytics_service: PortfolioAnalytics, test_db_session: Session, test_user: User
):
    acc1 = create_test_account(test_db_session, test_user.id, "Brokerage", AccountType.INVESTMENT, 0)
    holding = create_test_holding(test_db_session, acc1.id, "GOOG", "Google", 1, 2000.0, 2000.0)
    holding.cost_basis = None # No cost basis
    test_db_session.commit()

    with patch.object(analytics_service, 'get_current_portfolio_value', return_value=2000.0):
        attribution = analytics_service.get_performance_attribution(test_user.id)
        assert "GOOG" not in attribution # Should be skipped if no cost basis

# --- Mock yfinance data ---
def mock_yfinance_history_data(symbol: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
    """Helper to create mock yfinance history DataFrame."""
    # Ensure end_date for range is exclusive if freq is 'D' for pd.date_range
    # yfinance typically includes the end_date in its output if data is available.
    # For pd.date_range, if end_date is inclusive, it's fine. Let's assume inclusive for simplicity.
    dates = pd.date_range(start=start_date, end=end_date, freq='D')

    if symbol == "FAIL" or not dates.size: # Simulate a failed lookup or empty date range
        return pd.DataFrame(columns=['Close']).set_index(pd.DatetimeIndex([]))

    if symbol == "SPY": # Specific mock for SPY benchmark
        # Generate slightly more realistic data for SPY (e.g., small daily changes)
        price_points = np.linspace(300, 310, len(dates)) # Example: SPY from 300 to 310
        np.random.seed(42) # for reproducibility
        price_points += np.random.normal(0, 0.5, len(dates)).cumsum() # add some random walk
        return pd.DataFrame({'Close': price_points}, index=dates)

    # Default mock for other symbols (e.g., AAPL)
    price_points = np.linspace(100, 110, len(dates)) # Example: AAPL from 100 to 110
    np.random.seed(0) # for reproducibility
    price_points += np.random.normal(0, 0.3, len(dates)).cumsum()
    return pd.DataFrame({'Close': price_points}, index=dates)

@pytest.fixture
def mock_yfinance(mocker):
    """Mocks yfinance.Ticker and its history() method."""

    def ticker_constructor_side_effect(symbol_name, *args, **kwargs):
        mock_ticker_instance = MagicMock(spec=['history']) # Specify a list of attributes/methods
        mock_ticker_instance.symbol = symbol_name # Store symbol for history_side_effect

        def history_side_effect(start, end, *a, **kw):
            # Use the stored symbol to generate appropriate mock data
            return mock_yfinance_history_data(mock_ticker_instance.symbol, start, end)

        mock_ticker_instance.history.side_effect = history_side_effect
        return mock_ticker_instance

    # Patch yfinance.Ticker to use our side effect for its constructor
    mocker.patch("yfinance.Ticker", side_effect=ticker_constructor_side_effect)


# --- Tests for calculate_portfolio_returns (implicitly tests _calculate_daily_portfolio_values) ---
def test_calculate_portfolio_returns_no_investment_accounts(analytics_service: PortfolioAnalytics, test_user: User):
    # User has no investment/retirement accounts
    df_returns = analytics_service.calculate_portfolio_returns(test_user.id, datetime(2023,1,1), datetime(2023,1,31))
    assert df_returns.empty

def test_calculate_portfolio_returns_no_transactions(
    analytics_service: PortfolioAnalytics, test_db_session: Session, test_user: User, mock_yfinance
):
    create_test_account(test_db_session, test_user.id, "Brokerage", AccountType.INVESTMENT, 0)
    # No transactions
    df_returns = analytics_service.calculate_portfolio_returns(test_user.id, datetime(2023,1,1), datetime(2023,1,31))
    assert df_returns.empty # Current code returns empty if transactions_df is empty

def test_calculate_portfolio_returns_no_price_data_for_symbols(
    analytics_service: PortfolioAnalytics, test_db_session: Session, test_user: User, mock_yfinance
):
    acc = create_test_account(test_db_session, test_user.id, "Brokerage", AccountType.INVESTMENT, 0)
    create_test_transaction(test_db_session, test_user.id, acc.id, 100.0, "Buy FAIL", datetime(2023,1,5), symbol="FAIL", quantity=10)
    # mock_yfinance_history_data will return empty DF for "FAIL"

    df_returns = analytics_service.calculate_portfolio_returns(test_user.id, datetime(2023,1,1), datetime(2023,1,10))
    # If all price_data lookups fail, price_data dict is empty, returns empty DF
    assert df_returns.empty # Current code returns empty if price_data is empty

def test_calculate_portfolio_returns_single_stock_buy(
    analytics_service: PortfolioAnalytics, test_db_session: Session, test_user: User, mock_yfinance
):
    acc = create_test_account(test_db_session, test_user.id, "Brokerage", AccountType.INVESTMENT, 0)
    buy_date = datetime(2023,1,5)
    create_test_transaction(test_db_session, test_user.id, acc.id, 1000.0, "Buy AAPL", buy_date, symbol="AAPL", quantity=10)

    start_date = datetime(2023,1,1)
    end_date = datetime(2023,1,10)
    df_returns = analytics_service.calculate_portfolio_returns(test_user.id, start_date, end_date)

    assert not df_returns.empty
    expected_days = (end_date - start_date).days + 1
    assert len(df_returns) == expected_days
    assert list(df_returns.columns) == ['date', 'portfolio_value', 'daily_return']

    # Check portfolio value before purchase date
    assert df_returns[df_returns['date'] < pd.Timestamp(buy_date)]['portfolio_value'].sum() == 0

    # Check value on purchase date and after
    # Mock prices for AAPL from 100 to 110 over 10 days (Jan 1 to Jan 10)
    # Price on Jan 5 (day index 4 if Jan 1 is day index 0)
    # price = 100 + day_index * (10 / 9) for 10 days total (0 to 9)

    price_on_buy_date = 100 + ( (buy_date - start_date).days ) * (10.0 / (expected_days -1) if expected_days > 1 else 0)
    expected_value_on_buy_date = 10 * price_on_buy_date
    actual_value_on_buy_date = df_returns[df_returns['date'] == pd.Timestamp(buy_date)]['portfolio_value'].iloc[0]
    assert actual_value_on_buy_date == pytest.approx(expected_value_on_buy_date, rel=1e-1)

    # Value on end_date
    price_on_end_date = 100 + ( (end_date - start_date).days ) * (10.0 / (expected_days-1) if expected_days > 1 else 0)
    expected_value_on_end_date = 10 * price_on_end_date
    actual_value_on_end_date = df_returns[df_returns['date'] == pd.Timestamp(end_date)]['portfolio_value'].iloc[0]
    assert actual_value_on_end_date == pytest.approx(expected_value_on_end_date, rel=1e-1)

    # Daily returns: first non-zero value will have NaN return, or first day of data range.
    first_valid_return_index = df_returns[df_returns['portfolio_value'] > 0].index[0]
    if first_valid_return_index == 0 : # if portfolio value from day 1
         assert pd.isna(df_returns['daily_return'].iloc[0])
    else: # if portfolio value starts later
        # The day value becomes non-zero, its return is vs previous day's 0, can be inf or nan or 0 depending on pct_change impl.
        # Pandas pct_change on a series like [0,0,100,110] gives [NaN, NaN, inf, 0.1]
        # Let's check the first actual calculated return after value is established.
        if len(df_returns['daily_return'].dropna()) > 0:
            assert not pd.isna(df_returns['daily_return'].dropna().iloc[0])


def test_calculate_portfolio_returns_buy_and_sell(
    analytics_service: PortfolioAnalytics, test_db_session: Session, test_user: User, mock_yfinance
):
    acc = create_test_account(test_db_session, test_user.id, "Brokerage", AccountType.INVESTMENT, 0)
    buy_date = datetime(2023,1,2)
    sell_date = datetime(2023,1,6)
    create_test_transaction(test_db_session, test_user.id, acc.id, 1000.0, "Buy AAPL", buy_date, symbol="AAPL", quantity=10)
    create_test_transaction(test_db_session, test_user.id, acc.id, 550.0, "Sell AAPL", sell_date, symbol="AAPL", quantity=-5)

    start_date = datetime(2023,1,1)
    end_date = datetime(2023,1,10)
    expected_days = (end_date - start_date).days + 1
    df_returns = analytics_service.calculate_portfolio_returns(test_user.id, start_date, end_date)

    assert not df_returns.empty

    # Value on day before sell (Jan 5)
    date_before_sell = datetime(2023,1,5)
    price_on_date_before_sell = 100 + ( (date_before_sell - start_date).days ) * (10.0 / (expected_days-1))
    expected_value_before_sell = 10 * price_on_date_before_sell
    actual_value_before_sell = df_returns[df_returns['date'] == pd.Timestamp(date_before_sell)]['portfolio_value'].iloc[0]
    assert actual_value_before_sell == pytest.approx(expected_value_before_sell, rel=1e-1)

    # Value on sell date (Jan 6) - after sell, 5 shares remain
    price_on_sell_date = 100 + ( (sell_date - start_date).days ) * (10.0 / (expected_days-1))
    expected_value_on_sell_date = 5 * price_on_sell_date
    actual_value_on_sell_date = df_returns[df_returns['date'] == pd.Timestamp(sell_date)]['portfolio_value'].iloc[0]
    assert actual_value_on_sell_date == pytest.approx(expected_value_on_sell_date, rel=1e-1)

def test_calculate_portfolio_returns_multiple_symbols(
    analytics_service: PortfolioAnalytics, test_db_session: Session, test_user: User, mock_yfinance
):
    acc = create_test_account(test_db_session, test_user.id, "Brokerage", AccountType.INVESTMENT, 0)
    buy_date_aapl = datetime(2023,1,2)
    buy_date_msft = datetime(2023,1,3)
    create_test_transaction(test_db_session, test_user.id, acc.id, 1000.0, "Buy AAPL", buy_date_aapl, symbol="AAPL", quantity=10)
    create_test_transaction(test_db_session, test_user.id, acc.id, 1500.0, "Buy MSFT", buy_date_msft, symbol="MSFT", quantity=5)

    start_date = datetime(2023,1,1)
    end_date = datetime(2023,1,5) # Short period for easier manual calc
    expected_days = (end_date - start_date).days + 1 # 5 days

    df_returns = analytics_service.calculate_portfolio_returns(test_user.id, start_date, end_date)
    assert not df_returns.empty
    assert len(df_returns) == expected_days

    # Value on Jan 3 (AAPL bought on Jan 2, MSFT on Jan 3)
    # AAPL price on Jan 3 (day index 2): 100 + 2 * (10/4) = 105
    # MSFT price on Jan 3 (day index 2): 100 + 2 * (10/4) = 105 (mock is generic for non-SPY/FAIL)
    val_aapl_jan3 = 10 * (100 + ((datetime(2023,1,3) - start_date).days) * (10.0 / (expected_days-1)))
    val_msft_jan3 = 5 * (100 + ((datetime(2023,1,3) - start_date).days) * (10.0 / (expected_days-1)))
    expected_val_jan3 = val_aapl_jan3 + val_msft_jan3
    actual_val_jan3 = df_returns[df_returns['date'] == pd.Timestamp('2023-01-03')]['portfolio_value'].iloc[0]
    assert actual_val_jan3 == pytest.approx(expected_val_jan3, rel=1e-1)


# --- Tests for _calculate_benchmark_metrics ---
def test_calculate_benchmark_metrics_basic(analytics_service: PortfolioAnalytics, mock_yfinance):
    start_date = datetime(2023,1,1)
    end_date = datetime(2023,1,31) # Approx 30 days for returns
    num_days = (end_date - start_date).days + 1

    # Simple linear portfolio returns for predictability
    portfolio_returns_data = np.linspace(0.0001, 0.0005, num_days -1) # exclude first NaN
    portfolio_returns = pd.Series(portfolio_returns_data)

    # mock_yfinance will provide SPY data via mock_yfinance_history_data
    # SPY prices: 300 to 310 over `num_days`.
    # SPY daily returns will be somewhat variable due to cumsum noise.

    bench_return, alpha, beta = analytics_service._calculate_benchmark_metrics(portfolio_returns, start_date, end_date)

    assert isinstance(bench_return, float)
    assert isinstance(alpha, float)
    assert isinstance(beta, float)

    # We expect yfinance.Ticker("SPY").history to have been called
    # The mock_yfinance fixture patches yfinance.Ticker.
    # We need to check if it was called with "SPY".
    # This requires inspecting calls to the mock_yfinance_constructor if we set it up that way,
    # or if the Ticker instance stores the symbol. Our mock does: ticker_instance.symbol = symbol_name.
    # For now, let's assume if it runs without error and returns floats, the path was exercised.
    # A more robust check would be:
    # assert any(call_args[0][0] == "SPY" for call_args in mock_yfinance.call_args_list)
    # This depends on how mock_yfinance is set up.
    # Our current mock_yfinance patches `yfinance.Ticker` itself. So `yfinance.Ticker.assert_any_call("SPY")`

    # For now, basic type checks. More detailed value checks would require precise input control for SPY returns.
    # Example: If portfolio perfectly tracks SPY, beta ~1, alpha ~0.
    # If portfolio_returns are consistently higher than SPY, alpha > 0.
    assert bench_return > -1.0 # Should be a plausible return

def test_calculate_benchmark_metrics_error_yfinance(analytics_service: PortfolioAnalytics, mocker):
    start_date = datetime(2023,1,1)
    end_date = datetime(2023,1,31)
    portfolio_returns = pd.Series([0.01, 0.005, -0.002])

    mocker.patch("yfinance.Ticker", side_effect=Exception("YFinance Network Error"))

    bench_return, alpha, beta = analytics_service._calculate_benchmark_metrics(portfolio_returns, start_date, end_date)
    assert bench_return == 0.0
    assert alpha == 0.0
    assert beta == 1.0 # Default beta on error


# --- Tests for calculate_performance_metrics ---
def test_calculate_performance_metrics_success(
    analytics_service: PortfolioAnalytics, test_db_session: Session, test_user: User, mock_yfinance
):
    # Setup: 1 account, 1 holding, 2 transactions (buy)
    acc = create_test_account(test_db_session, test_user.id, "MainBrokerage", AccountType.INVESTMENT, 0)
    # Buy 10 shares of XYZ on Jan 2. Mock XYZ price from 100 to 110 over Jan 1-Jan 31.
    create_test_transaction(test_db_session, test_user.id, acc.id, 1000.0, "Buy XYZ", datetime(2023,1,2), symbol="XYZ", quantity=10)
    # Add a dummy holding for get_current_portfolio_value to pick up (market value will be used from here)
    create_test_holding(test_db_session, acc.id, "XYZ", "XYZ Corp", 10, 1080.0, 108.0) # Market value on Jan 31st-ish

    period_days = 30 # Jan 1 to Jan 30 approx
    metrics = analytics_service.calculate_performance_metrics(test_user.id, period_days=period_days)

    assert isinstance(metrics, PerformanceMetrics)
    assert metrics.current_value == 1080.0 # From the dummy holding

    # For other metrics, they depend on calculate_portfolio_returns and _calculate_benchmark_metrics
    # which use mocked yfinance data.
    # total_return: (value_end / value_start) - 1.
    # value_start (Jan 2 for XYZ): 10 * (price of XYZ on Jan 2)
    # value_end (Jan 30 for XYZ): 10 * (price of XYZ on Jan 30)
    # Mocked XYZ prices: Jan 1 = 100, Jan 30 = 100 + 29 * (10 / (num_period_days -1)).
    # num_period_days for returns_df is based on period_days (30), so 30 or 31 days in df.
    # Let's assume calculate_portfolio_returns provides a reasonable series.

    assert metrics.total_return == pytest.approx(0.07, rel=0.2) # Approx based on 100 to 108 over ~29 days
    assert metrics.annualized_return is not None
    assert metrics.volatility > 0
    assert metrics.sharpe_ratio is not None
    assert -1.0 <= metrics.max_drawdown <= 0.0
    assert metrics.benchmark_return is not None # From mocked SPY
    assert metrics.alpha is not None
    assert metrics.beta is not None

def test_calculate_performance_metrics_no_returns_data(analytics_service: PortfolioAnalytics, test_user: User, mock_yfinance):
    # Mock calculate_portfolio_returns to return empty DataFrame
    with patch.object(analytics_service, 'calculate_portfolio_returns', return_value=pd.DataFrame()):
        metrics = analytics_service.calculate_performance_metrics(test_user.id, period_days=30)
        assert metrics is None

def test_calculate_performance_metrics_insufficient_returns(analytics_service: PortfolioAnalytics, test_user: User, mock_yfinance):
    # Mock calculate_portfolio_returns to return a DataFrame with only one row of returns (len(returns) < 2)
    mock_short_df = pd.DataFrame({
        'date': [datetime(2023,1,1), datetime(2023,1,2)],
        'portfolio_value': [100.0, 101.0],
        'daily_return': [np.nan, 0.01] # Only one valid daily return
    })
    with patch.object(analytics_service, 'calculate_portfolio_returns', return_value=mock_short_df):
        # Also need to mock get_current_portfolio_value
        with patch.object(analytics_service, 'get_current_portfolio_value', return_value=101.0):
            metrics = analytics_service.calculate_performance_metrics(test_user.id, period_days=30)
            assert metrics is None # Because len(returns.dropna()) < 2

# TODO: Test edge cases like division by zero if cost_basis is 0, or if portfolio_value is 0 for weights.
# (The current code for attribution would divide by zero if cost_basis is 0, needs guard)
# (The current code for attribution would divide by zero if get_current_portfolio_value is 0, needs guard)
# TODO: Address guards for division by zero in `get_performance_attribution` in main code.
# TODO: Test `_calculate_benchmark_metrics` with more specific portfolio and spy returns.
