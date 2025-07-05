import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal
from services.app.alpaca_service import AlpacaService, execute_trade

@pytest.fixture
def mock_alpaca_api():
    """Mock Alpaca API for testing"""
    with patch('services.app.alpaca_service.REST') as mock_rest:
        mock_api = Mock()
        mock_rest.return_value = mock_api
        yield mock_api

@pytest.fixture
def alpaca_service(mock_alpaca_api):
    """Create AlpacaService instance with mocked API"""
    with patch.dict(os.environ, {
        'ALPACA_API_KEY': 'test_key',
        'ALPACA_API_SECRET': 'test_secret',
        'ALPACA_BASE_URL': 'https://paper-api.alpaca.markets'
    }):
        service = AlpacaService()
        return service

class TestAlpacaService:
    
    def test_init_with_credentials(self, mock_alpaca_api):
        """Test AlpacaService initialization with credentials"""
        with patch.dict(os.environ, {
            'ALPACA_API_KEY': 'test_key',
            'ALPACA_API_SECRET': 'test_secret'
        }):
            service = AlpacaService()
            assert service.api_key == 'test_key'
            assert service.api_secret == 'test_secret'
            assert service.api is not None
    
    def test_init_without_credentials(self):
        """Test AlpacaService initialization without credentials"""
        with patch.dict(os.environ, {}, clear=True):
            service = AlpacaService()
            assert service.api is None
    
    def test_is_connected_success(self, alpaca_service, mock_alpaca_api):
        """Test successful connection check"""
        mock_account = Mock()
        mock_alpaca_api.get_account.return_value = mock_account
        
        result = alpaca_service.is_connected()
        assert result is True
        mock_alpaca_api.get_account.assert_called_once()
    
    def test_is_connected_failure(self, alpaca_service, mock_alpaca_api):
        """Test connection check failure"""
        mock_alpaca_api.get_account.side_effect = Exception("Connection failed")
        
        result = alpaca_service.is_connected()
        assert result is False
    
    def test_is_connected_no_api(self):
        """Test connection check with no API"""
        service = AlpacaService()
        service.api = None
        
        result = service.is_connected()
        assert result is False
    
    def test_get_account_success(self, alpaca_service, mock_alpaca_api):
        """Test successful account retrieval"""
        mock_account = Mock()
        mock_account.id = "test_id"
        mock_account.account_number = "123456789"
        mock_account.status = "ACTIVE"
        mock_account.currency = "USD"
        mock_account.buying_power = "10000.00"
        mock_account.cash = "5000.00"
        mock_account.portfolio_value = "15000.00"
        mock_account.equity = "15000.00"
        mock_account.last_equity = "14500.00"
        mock_account.multiplier = "1"
        mock_account.day_trade_count = "0"
        mock_account.daytrade_buying_power = "0.00"
        mock_account.regt_buying_power = "10000.00"
        mock_account.initial_margin = "0.00"
        mock_account.maintenance_margin = "0.00"
        mock_account.pattern_day_trader = False
        mock_account.trading_blocked = False
        mock_account.transfers_blocked = False
        mock_account.account_blocked = False
        mock_account.created_at = None
        mock_account.trade_suspended_by_user = False
        mock_account.shorting_enabled = True
        mock_account.long_market_value = "10000.00"
        mock_account.short_market_value = "0.00"
        
        mock_alpaca_api.get_account.return_value = mock_account
        
        result = alpaca_service.get_account()
        
        assert result["id"] == "test_id"
        assert result["account_number"] == "123456789"
        assert result["status"] == "ACTIVE"
        assert result["buying_power"] == 10000.00
        assert result["cash"] == 5000.00
        assert result["portfolio_value"] == 15000.00
    
    def test_get_account_no_api(self):
        """Test account retrieval with no API"""
        service = AlpacaService()
        service.api = None
        
        result = service.get_account()
        assert result is None
    
    def test_get_positions_success(self, alpaca_service, mock_alpaca_api):
        """Test successful positions retrieval"""
        mock_position = Mock()
        mock_position.symbol = "AAPL"
        mock_position.qty = "100"
        mock_position.side = "long"
        mock_position.market_value = "15000.00"
        mock_position.cost_basis = "14000.00"
        mock_position.unrealized_pl = "1000.00"
        mock_position.unrealized_plpc = "0.0714"
        mock_position.current_price = "150.00"
        mock_position.lastday_price = "148.00"
        mock_position.change_today = "2.00"
        mock_position.avg_entry_price = "140.00"
        mock_position.asset_id = "test_asset_id"
        mock_position.asset_class = "us_equity"
        mock_position.exchange = "NASDAQ"
        
        mock_alpaca_api.list_positions.return_value = [mock_position]
        
        result = alpaca_service.get_positions()
        
        assert len(result) == 1
        assert result[0]["symbol"] == "AAPL"
        assert result[0]["quantity"] == 100.0
        assert result[0]["side"] == "long"
        assert result[0]["market_value"] == 15000.00
    
    def test_get_positions_no_api(self):
        """Test positions retrieval with no API"""
        service = AlpacaService()
        service.api = None
        
        result = service.get_positions()
        assert result == []
    
    def test_submit_order_success(self, alpaca_service, mock_alpaca_api):
        """Test successful order submission"""
        mock_order = Mock()
        mock_order.id = "test_order_id"
        mock_order.client_order_id = "client_123"
        mock_order.symbol = "AAPL"
        mock_order.qty = "100"
        mock_order.side = "buy"
        mock_order.order_type = "market"
        mock_order.time_in_force = "day"
        mock_order.limit_price = None
        mock_order.stop_price = None
        mock_order.trail_percent = None
        mock_order.trail_price = None
        mock_order.status = "new"
        mock_order.created_at = None
        mock_order.updated_at = None
        mock_order.submitted_at = None
        mock_order.filled_at = None
        mock_order.expired_at = None
        mock_order.canceled_at = None
        mock_order.failed_at = None
        mock_order.replaced_at = None
        mock_order.replaced_by = None
        mock_order.replaces = None
        mock_order.asset_id = "test_asset"
        mock_order.asset_class = "us_equity"
        mock_order.notional = None
        mock_order.filled_qty = None
        mock_order.filled_avg_price = None
        mock_order.order_class = "simple"
        mock_order.type = "market"
        mock_order.amount = None
        mock_order.hwm = None
        mock_order.commission = None
        mock_order.extended_hours = False
        
        mock_alpaca_api.submit_order.return_value = mock_order
        
        result = alpaca_service.submit_order(
            symbol="AAPL",
            qty=100,
            side="buy",
            order_type="market"
        )
        
        assert result["id"] == "test_order_id"
        assert result["symbol"] == "AAPL"
        assert result["qty"] == 100.0
        assert result["side"] == "buy"
        assert result["order_type"] == "market"
    
    def test_submit_order_no_api(self):
        """Test order submission with no API"""
        service = AlpacaService()
        service.api = None
        
        with pytest.raises(Exception):
            service.submit_order("AAPL", 100, "buy")
    
    def test_get_order_success(self, alpaca_service, mock_alpaca_api):
        """Test successful order retrieval"""
        mock_order = Mock()
        mock_order.id = "test_order_id"
        mock_order.client_order_id = "client_123"
        mock_order.symbol = "AAPL"
        mock_order.qty = "100"
        mock_order.side = "buy"
        mock_order.order_type = "market"
        mock_order.time_in_force = "day"
        mock_order.limit_price = None
        mock_order.stop_price = None
        mock_order.status = "filled"
        mock_order.created_at = None
        mock_order.updated_at = None
        mock_order.submitted_at = None
        mock_order.filled_at = None
        mock_order.filled_qty = "100"
        mock_order.filled_avg_price = "150.00"
        mock_order.commission = "0.00"
        mock_order.extended_hours = False
        
        mock_alpaca_api.get_order.return_value = mock_order
        
        result = alpaca_service.get_order("test_order_id")
        
        assert result["id"] == "test_order_id"
        assert result["symbol"] == "AAPL"
        assert result["status"] == "filled"
        assert result["filled_qty"] == 100.0
        assert result["filled_avg_price"] == 150.00
    
    def test_get_order_no_api(self):
        """Test order retrieval with no API"""
        service = AlpacaService()
        service.api = None
        
        result = service.get_order("test_order_id")
        assert result is None
    
    def test_cancel_order_success(self, alpaca_service, mock_alpaca_api):
        """Test successful order cancellation"""
        mock_alpaca_api.cancel_order.return_value = None
        
        result = alpaca_service.cancel_order("test_order_id")
        assert result is True
        mock_alpaca_api.cancel_order.assert_called_once_with("test_order_id")
    
    def test_cancel_order_failure(self, alpaca_service, mock_alpaca_api):
        """Test order cancellation failure"""
        mock_alpaca_api.cancel_order.side_effect = Exception("Cancel failed")
        
        result = alpaca_service.cancel_order("test_order_id")
        assert result is False
    
    def test_cancel_order_no_api(self):
        """Test order cancellation with no API"""
        service = AlpacaService()
        service.api = None
        
        result = service.cancel_order("test_order_id")
        assert result is False

class TestExecuteTradeFunction:
    
    def test_execute_trade_connected(self, mock_alpaca_api):
        """Test execute_trade function with connected service"""
        with patch.dict(os.environ, {
            'ALPACA_API_KEY': 'test_key',
            'ALPACA_API_SECRET': 'test_secret'
        }):
            # Properly mock the order with all required attributes
            mock_order = Mock()
            mock_order.id = "test_order_id"
            mock_order.client_order_id = None
            mock_order.symbol = "AAPL"
            mock_order.qty = "100"
            mock_order.side = "buy"
            mock_order.order_type = "market"
            mock_order.time_in_force = "day"
            mock_order.limit_price = None
            mock_order.stop_price = None
            mock_order.trail_percent = None
            mock_order.trail_price = None
            mock_order.status = "new"
            mock_order.created_at = None
            mock_order.updated_at = None
            mock_order.submitted_at = None
            mock_order.filled_at = None
            mock_order.expired_at = None
            mock_order.canceled_at = None
            mock_order.failed_at = None
            mock_order.replaced_at = None
            mock_order.replaced_by = None
            mock_order.replaces = None
            mock_order.asset_id = "test_asset"
            mock_order.asset_class = "us_equity"
            mock_order.notional = None
            mock_order.filled_qty = None
            mock_order.filled_avg_price = None
            mock_order.order_class = "simple"
            mock_order.type = "market"
            mock_order.amount = None
            mock_order.hwm = None
            mock_order.commission = None
            mock_order.extended_hours = False
            
            mock_alpaca_api.submit_order.return_value = mock_order
            mock_alpaca_api.get_account.return_value = Mock()
            
            result = execute_trade("AAPL", 100, "buy")
            
            assert result["symbol"] == "AAPL"
            assert result["quantity"] == 100
            assert result["action"] == "buy"
            assert result["status"] == "submitted"
            assert result["order_id"] == "test_order_id"
    
    def test_execute_trade_not_connected(self):
        """Test execute_trade function with no connection"""
        with patch.dict(os.environ, {}, clear=True):
            result = execute_trade("AAPL", 100, "buy")
            
            assert result["symbol"] == "AAPL"
            assert result["quantity"] == 100
            assert result["action"] == "buy"
            assert result["status"] == "simulated"
    
    def test_execute_trade_error(self, mock_alpaca_api):
        """Test execute_trade function with error"""
        with patch.dict(os.environ, {
            'ALPACA_API_KEY': 'test_key',
            'ALPACA_API_SECRET': 'test_secret'
        }):
            mock_alpaca_api.get_account.return_value = Mock()
            mock_alpaca_api.submit_order.side_effect = Exception("Order failed")
            
            result = execute_trade("AAPL", 100, "buy")
            
            assert result["symbol"] == "AAPL"
            assert result["quantity"] == 100
            assert result["action"] == "buy"
            assert result["status"] == "failed"
            assert "error" in result