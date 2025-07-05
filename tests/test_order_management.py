import pytest
import os
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from services.app.database import Base
from services.app.order_management import (
    OrderManagementSystem, Order, OrderRequest, OrderType, OrderSide, 
    OrderStatus, TimeInForce
)

@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture
def mock_alpaca_service():
    """Mock AlpacaService for testing"""
    mock_service = Mock()
    mock_service.is_connected.return_value = True
    mock_service.submit_order.return_value = {
        "id": "alpaca_order_123",
        "status": "new",
        "symbol": "AAPL",
        "qty": 100,
        "side": "buy",
        "order_type": "market"
    }
    mock_service.get_order.return_value = {
        "id": "alpaca_order_123",
        "status": "filled",
        "filled_qty": 100,
        "filled_avg_price": 150.00,
        "commission": 0.00
    }
    mock_service.cancel_order.return_value = True
    return mock_service

@pytest.fixture
def order_management_system(db_session, mock_alpaca_service):
    """Create OrderManagementSystem instance"""
    with patch('services.app.order_management.AlpacaService') as mock_alpaca_class:
        mock_alpaca_class.return_value = mock_alpaca_service
        oms = OrderManagementSystem(db_session)
        return oms

@pytest.fixture
def sample_order_request():
    """Create a sample order request"""
    return OrderRequest(
        symbol="AAPL",
        side=OrderSide.BUY,
        quantity=100,
        order_type=OrderType.MARKET,
        time_in_force=TimeInForce.DAY
    )

@pytest.fixture
def sample_limit_order_request():
    """Create a sample limit order request"""
    return OrderRequest(
        symbol="AAPL",
        side=OrderSide.BUY,
        quantity=100,
        order_type=OrderType.LIMIT,
        time_in_force=TimeInForce.DAY,
        limit_price=150.00
    )

class TestOrderModel:
    
    def test_order_creation(self, db_session):
        """Test creating an order in the database"""
        order = Order(
            user_id=1,
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=Decimal("100"),
            order_type=OrderType.MARKET,
            time_in_force=TimeInForce.DAY,
            status=OrderStatus.PENDING
        )
        
        db_session.add(order)
        db_session.commit()
        db_session.refresh(order)
        
        assert order.id is not None
        assert order.user_id == 1
        assert order.symbol == "AAPL"
        assert order.side == OrderSide.BUY
        assert order.quantity == Decimal("100")
        assert order.order_type == OrderType.MARKET
        assert order.status == OrderStatus.PENDING
        assert order.created_at is not None
    
    def test_order_to_dict(self, db_session):
        """Test converting order to dictionary"""
        order = Order(
            user_id=1,
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=Decimal("100"),
            order_type=OrderType.MARKET,
            time_in_force=TimeInForce.DAY,
            status=OrderStatus.PENDING
        )
        
        db_session.add(order)
        db_session.commit()
        db_session.refresh(order)
        
        order_dict = order.to_dict()
        
        assert order_dict["id"] == order.id
        assert order_dict["user_id"] == 1
        assert order_dict["symbol"] == "AAPL"
        assert order_dict["side"] == "buy"
        assert order_dict["quantity"] == Decimal("100")
        assert order_dict["order_type"] == "market"
        assert order_dict["status"] == "pending"

class TestOrderRequest:
    
    def test_order_request_creation(self):
        """Test creating an order request"""
        request = OrderRequest(
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.MARKET
        )
        
        assert request.symbol == "AAPL"
        assert request.side == OrderSide.BUY
        assert request.quantity == 100
        assert request.order_type == OrderType.MARKET
        assert request.time_in_force == TimeInForce.DAY  # Default value
    
    def test_limit_order_request(self):
        """Test creating a limit order request"""
        request = OrderRequest(
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.LIMIT,
            limit_price=150.00
        )
        
        assert request.limit_price == 150.00

class TestOrderManagementSystem:
    
    def test_create_order(self, order_management_system, sample_order_request):
        """Test creating an order"""
        order = order_management_system.create_order(
            user_id=1,
            order_request=sample_order_request
        )
        
        assert order.id is not None
        assert order.user_id == 1
        assert order.symbol == "AAPL"
        assert order.side == OrderSide.BUY
        assert order.quantity == Decimal("100")
        assert order.order_type == OrderType.MARKET
        assert order.status == OrderStatus.PENDING
    
    def test_create_order_with_strategy(self, order_management_system, sample_order_request):
        """Test creating an order with strategy ID"""
        order = order_management_system.create_order(
            user_id=1,
            order_request=sample_order_request,
            strategy_id=123
        )
        
        assert order.strategy_id == 123
    
    def test_submit_order_success(self, order_management_system, sample_order_request, mock_alpaca_service):
        """Test successful order submission"""
        # Create order
        order = order_management_system.create_order(
            user_id=1,
            order_request=sample_order_request
        )
        
        # Submit order
        result = order_management_system.submit_order(order.id)
        
        assert result is True
        assert order.status == OrderStatus.SUBMITTED
        assert order.broker_order_id == "alpaca_order_123"
        assert order.submitted_at is not None
        
        # Verify Alpaca service was called correctly
        mock_alpaca_service.submit_order.assert_called_once_with(
            symbol="AAPL",
            qty=100.0,
            side="buy",
            order_type="market",
            time_in_force="day",
            limit_price=None,
            stop_price=None,
            trail_percent=None,
            trail_price=None,
            extended_hours=False,
            client_order_id=None
        )
    
    def test_submit_order_alpaca_not_connected(self, order_management_system, sample_order_request, mock_alpaca_service):
        """Test order submission when Alpaca is not connected"""
        mock_alpaca_service.is_connected.return_value = False
        
        # Create order
        order = order_management_system.create_order(
            user_id=1,
            order_request=sample_order_request
        )
        
        # Submit order
        result = order_management_system.submit_order(order.id)
        
        assert result is True
        assert order.status == OrderStatus.SUBMITTED
        assert order.broker_order_id.startswith("simulated_broker_id_")
        assert order.submitted_at is not None
    
    def test_submit_order_invalid_status(self, order_management_system, sample_order_request):
        """Test submitting order with invalid status"""
        # Create order
        order = order_management_system.create_order(
            user_id=1,
            order_request=sample_order_request
        )
        
        # Change status to submitted
        order.status = OrderStatus.SUBMITTED
        order_management_system.db.commit()
        
        # Try to submit again
        with pytest.raises(ValueError, match="cannot be submitted"):
            order_management_system.submit_order(order.id)
    
    def test_submit_order_not_found(self, order_management_system):
        """Test submitting non-existent order"""
        with pytest.raises(ValueError, match="Order .* not found"):
            order_management_system.submit_order(999)
    
    def test_cancel_order_success(self, order_management_system, sample_order_request, mock_alpaca_service):
        """Test successful order cancellation"""
        # Create and submit order
        order = order_management_system.create_order(
            user_id=1,
            order_request=sample_order_request
        )
        order_management_system.submit_order(order.id)
        
        # Cancel order
        result = order_management_system.cancel_order(order.id)
        
        assert result is True
        assert order.status == OrderStatus.CANCELLED
        assert order.updated_at is not None
        
        # Verify Alpaca service was called
        mock_alpaca_service.cancel_order.assert_called_once_with("alpaca_order_123")
    
    def test_cancel_order_invalid_status(self, order_management_system, sample_order_request):
        """Test cancelling order with invalid status"""
        # Create order
        order = order_management_system.create_order(
            user_id=1,
            order_request=sample_order_request
        )
        
        # Change status to filled
        order.status = OrderStatus.FILLED
        order_management_system.db.commit()
        
        # Try to cancel
        with pytest.raises(ValueError, match="cannot be cancelled"):
            order_management_system.cancel_order(order.id)
    
    def test_cancel_order_not_found(self, order_management_system):
        """Test cancelling non-existent order"""
        with pytest.raises(ValueError, match="Order .* not found"):
            order_management_system.cancel_order(999)
    
    def test_get_user_orders(self, order_management_system, sample_order_request):
        """Test retrieving user orders"""
        # Create multiple orders
        order1 = order_management_system.create_order(
            user_id=1,
            order_request=sample_order_request
        )
        
        order2_request = OrderRequest(
            symbol="GOOGL",
            side=OrderSide.SELL,
            quantity=50,
            order_type=OrderType.LIMIT,
            limit_price=2800.00
        )
        order2 = order_management_system.create_order(
            user_id=1,
            order_request=order2_request
        )
        
        # Create order for different user
        order3 = order_management_system.create_order(
            user_id=2,
            order_request=sample_order_request
        )
        
        # Get orders for user 1
        user_orders = order_management_system.get_user_orders(user_id=1)
        
        assert len(user_orders) == 2
        assert all(order.user_id == 1 for order in user_orders)
    
    def test_get_user_orders_with_filters(self, order_management_system, sample_order_request):
        """Test retrieving user orders with filters"""
        # Create order
        order = order_management_system.create_order(
            user_id=1,
            order_request=sample_order_request
        )
        
        # Test status filter
        pending_orders = order_management_system.get_user_orders(
            user_id=1,
            status=OrderStatus.PENDING
        )
        assert len(pending_orders) == 1
        assert pending_orders[0].status == OrderStatus.PENDING
        
        # Test symbol filter
        aapl_orders = order_management_system.get_user_orders(
            user_id=1,
            symbol="AAPL"
        )
        assert len(aapl_orders) == 1
        assert aapl_orders[0].symbol == "AAPL"
    
    def test_get_open_orders(self, order_management_system, sample_order_request):
        """Test retrieving open orders"""
        # Create orders with different statuses
        order1 = order_management_system.create_order(
            user_id=1,
            order_request=sample_order_request
        )
        
        order2 = order_management_system.create_order(
            user_id=1,
            order_request=sample_order_request
        )
        order2.status = OrderStatus.SUBMITTED
        order_management_system.db.commit()
        
        order3 = order_management_system.create_order(
            user_id=1,
            order_request=sample_order_request
        )
        order3.status = OrderStatus.FILLED
        order_management_system.db.commit()
        
        # Get open orders
        open_orders = order_management_system.get_open_orders(user_id=1)
        
        assert len(open_orders) == 2
        assert all(order.status in [OrderStatus.PENDING, OrderStatus.SUBMITTED] for order in open_orders)
    
    def test_get_order_performance(self, order_management_system, sample_order_request):
        """Test getting order performance metrics"""
        # Create orders with different statuses
        order1 = order_management_system.create_order(
            user_id=1,
            order_request=sample_order_request
        )
        order1.status = OrderStatus.FILLED
        order1.commission = Decimal("1.00")
        
        order2 = order_management_system.create_order(
            user_id=1,
            order_request=sample_order_request
        )
        order2.status = OrderStatus.CANCELLED
        
        order3 = order_management_system.create_order(
            user_id=1,
            order_request=sample_order_request
        )
        order3.status = OrderStatus.REJECTED
        
        order_management_system.db.commit()
        
        # Get performance metrics
        performance = order_management_system.get_order_performance(user_id=1)
        
        assert performance["total_orders"] == 3
        assert performance["filled_orders"] == 1
        assert performance["cancelled_orders"] == 1
        assert performance["rejected_orders"] == 1
        assert performance["fill_rate"] == 33.33333333333333
        assert performance["total_commission"] == Decimal("1.00")
    
    def test_validate_order_request_invalid_quantity(self, order_management_system):
        """Test order request validation with invalid quantity"""
        invalid_request = OrderRequest(
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=0,  # Invalid quantity
            order_type=OrderType.MARKET
        )
        
        with pytest.raises(ValueError, match="Quantity must be positive"):
            order_management_system.create_order(
                user_id=1,
                order_request=invalid_request
            )
    
    def test_validate_limit_order_without_price(self, order_management_system):
        """Test limit order validation without limit price"""
        invalid_request = OrderRequest(
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.LIMIT
            # Missing limit_price
        )
        
        with pytest.raises(ValueError, match="Limit price required for limit orders"):
            order_management_system.create_order(
                user_id=1,
                order_request=invalid_request
            )
    
    def test_validate_stop_order_without_price(self, order_management_system):
        """Test stop order validation without stop price"""
        invalid_request = OrderRequest(
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.STOP
            # Missing stop_price
        )
        
        with pytest.raises(ValueError, match="Stop price required for stop orders"):
            order_management_system.create_order(
                user_id=1,
                order_request=invalid_request
            )
    
    def test_validate_trailing_stop_without_params(self, order_management_system):
        """Test trailing stop order validation without trail parameters"""
        invalid_request = OrderRequest(
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.TRAILING_STOP
            # Missing trail_percent and trail_price
        )
        
        with pytest.raises(ValueError, match="Trail percent or trail price required"):
            order_management_system.create_order(
                user_id=1,
                order_request=invalid_request
            )

class TestOrderStatusUpdates:
    
    def test_update_order_status_success(self, order_management_system, sample_order_request, mock_alpaca_service):
        """Test successful order status update"""
        # Create and submit order
        order = order_management_system.create_order(
            user_id=1,
            order_request=sample_order_request
        )
        order_management_system.submit_order(order.id)
        
        # Update status
        updated_order = order_management_system.update_order_status(order.id)
        
        assert updated_order.status == OrderStatus.FILLED
        assert updated_order.filled_quantity == Decimal("100")
        assert updated_order.average_fill_price == Decimal("150.00")
        assert updated_order.commission == Decimal("0.00")
        
        # Verify Alpaca service was called
        mock_alpaca_service.get_order.assert_called_once_with("alpaca_order_123")
    
    def test_update_order_status_no_broker_id(self, order_management_system, sample_order_request):
        """Test updating order status without broker ID"""
        # Create order without submitting
        order = order_management_system.create_order(
            user_id=1,
            order_request=sample_order_request
        )
        
        # Update status
        updated_order = order_management_system.update_order_status(order.id)
        
        assert updated_order == order
        assert updated_order.status == OrderStatus.PENDING
    
    def test_batch_update_order_statuses(self, order_management_system, sample_order_request, mock_alpaca_service):
        """Test batch updating order statuses"""
        # Create and submit multiple orders
        order1 = order_management_system.create_order(
            user_id=1,
            order_request=sample_order_request
        )
        order_management_system.submit_order(order1.id)
        
        order2 = order_management_system.create_order(
            user_id=1,
            order_request=sample_order_request
        )
        order_management_system.submit_order(order2.id)
        
        # Batch update
        updated_count = order_management_system.batch_update_order_statuses(user_id=1)
        
        assert updated_count == 2
        assert mock_alpaca_service.get_order.call_count == 2