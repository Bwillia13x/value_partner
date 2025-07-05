from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, Enum, Numeric
from enum import Enum as PyEnum
import json
import logging
from dataclasses import dataclass

from .database import Base
# # from .alpaca_service import AlpacaService # Removed for debugging # Removed for debugging

logger = logging.getLogger(__name__)

class OrderType(PyEnum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    TRAILING_STOP = "trailing_stop"

class OrderSide(PyEnum):
    BUY = "buy"
    SELL = "sell"

class OrderStatus(PyEnum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"

class TimeInForce(PyEnum):
    DAY = "day"
    GTC = "gtc"  # Good Till Cancelled
    IOC = "ioc"  # Immediate Or Cancel
    FOK = "fok"  # Fill Or Kill

@dataclass
class OrderRequest:
    """Order request data structure"""
    symbol: str
    side: OrderSide
    quantity: float
    order_type: OrderType
    time_in_force: TimeInForce = TimeInForce.DAY
    limit_price: Optional[float] = None  # Note: Consider using Decimal in API layer
    stop_price: Optional[float] = None   # Note: Consider using Decimal in API layer
    trail_percent: Optional[float] = None
    trail_price: Optional[float] = None
    extended_hours: bool = False
    client_order_id: Optional[str] = None

class Order(Base):
    """Order model for database storage"""
    __tablename__ = "orders"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id"), nullable=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=True)
    
    # Order details
    symbol = Column(String, nullable=False)
    side = Column(Enum(OrderSide), nullable=False)
    quantity = Column(Numeric(15, 6), nullable=False)
    order_type = Column(Enum(OrderType), nullable=False)
    time_in_force = Column(Enum(TimeInForce), default=TimeInForce.DAY)
    
    # Pricing
    limit_price = Column(Numeric(12, 4), nullable=True)
    stop_price = Column(Numeric(12, 4), nullable=True)
    trail_percent = Column(Numeric(5, 4), nullable=True)
    trail_price = Column(Numeric(12, 4), nullable=True)
    
    # Execution details
    filled_quantity = Column(Numeric(15, 6), default=0.0)
    average_fill_price = Column(Numeric(12, 4), nullable=True)
    commission = Column(Numeric(10, 2), nullable=True)
    
    # Status and tracking
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    broker_order_id = Column(String, nullable=True)
    client_order_id = Column(String, nullable=True)
    
    # Additional options
    extended_hours = Column(Boolean, default=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    submitted_at = Column(DateTime, nullable=True)
    filled_at = Column(DateTime, nullable=True)
    
    # JSON field for additional broker-specific data
    broker_data = Column(Text, nullable=True)
    
    def to_dict(self) -> Dict:
        """Convert order to dictionary"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "account_id": self.account_id,
            "strategy_id": self.strategy_id,
            "symbol": self.symbol,
            "side": self.side.value,
            "quantity": self.quantity,
            "order_type": self.order_type.value,
            "time_in_force": self.time_in_force.value,
            "limit_price": self.limit_price,
            "stop_price": self.stop_price,
            "trail_percent": self.trail_percent,
            "trail_price": self.trail_price,
            "filled_quantity": self.filled_quantity,
            "average_fill_price": self.average_fill_price,
            "commission": self.commission,
            "status": self.status.value,
            "broker_order_id": self.broker_order_id,
            "client_order_id": self.client_order_id,
            "extended_hours": self.extended_hours,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "submitted_at": self.submitted_at.isoformat() if self.submitted_at else None,
            "filled_at": self.filled_at.isoformat() if self.filled_at else None,
            "broker_data": json.loads(self.broker_data) if self.broker_data else None
        }

class OrderManagementSystem:
    """Advanced order management system"""
    
    def __init__(self, db: Session):
        self.db = db
        # self.alpaca_service = AlpacaService() # Removed for debugging
        
    def create_order(self, user_id: int, order_request: OrderRequest, 
                    account_id: Optional[int] = None, 
                    strategy_id: Optional[int] = None) -> Order:
        """Create a new order"""
        
        # Validate order request
        self._validate_order_request(order_request)
        
        # Create order in database
        order = Order(
            user_id=user_id,
            account_id=account_id,
            strategy_id=strategy_id,
            symbol=order_request.symbol,
            side=order_request.side,
            quantity=order_request.quantity,
            order_type=order_request.order_type,
            time_in_force=order_request.time_in_force,
            limit_price=order_request.limit_price,
            stop_price=order_request.stop_price,
            trail_percent=order_request.trail_percent,
            trail_price=order_request.trail_price,
            extended_hours=order_request.extended_hours,
            client_order_id=order_request.client_order_id
        )
        
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        
        logger.info(f"Created order {order.id} for user {user_id}")
        return order
        
    def submit_order(self, order_id: int) -> bool:
        """Submit order to broker"""
        
        order = self.db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise ValueError(f"Order {order_id} not found")
            
        if order.status != OrderStatus.PENDING:
            raise ValueError(f"Order {order_id} cannot be submitted (status: {order.status})")
            
        try:
            # Simulate Alpaca order submission
            broker_order = {
                "id": "simulated_broker_id_" + str(order_id),
                "status": "submitted",
                "filled_qty": 0,
                "filled_avg_price": 0,
                "commission": 0,
                "filled_at": None
            }
            logger.info(f"Simulated Alpaca order submission for order {order_id}")
            logger.info(f"Simulated Alpaca order submission for order {order_id}")
            
            # Update order with broker information
            order.broker_order_id = broker_order.get("id")
            order.status = OrderStatus.SUBMITTED
            order.submitted_at = datetime.utcnow()
            order.broker_data = json.dumps(broker_order)
            
            self.db.commit()
            
            logger.info(f"Submitted order {order_id} to broker")
            return True
            
        except Exception as e:
            order.status = OrderStatus.REJECTED
            self.db.commit()
            logger.error(f"Failed to submit order {order_id}: {e}")
            return False
            
    def cancel_order(self, order_id: int) -> bool:
        """Cancel an order"""
        
        order = self.db.query(Order).filter(Order.id == order_id).first()
        if not order:
            raise ValueError(f"Order {order_id} not found")
            
        if order.status not in [OrderStatus.PENDING, OrderStatus.SUBMITTED]:
            raise ValueError(f"Order {order_id} cannot be cancelled (status: {order.status})")
            
        try:
            # Simulate broker cancellation
            if order.broker_order_id:
                logger.info(f"Simulated Alpaca order cancellation for order {order.broker_order_id}")
                success = True # Simulate success
                if not success:
                    return False
                    
            # Update order status
            order.status = OrderStatus.CANCELLED
            order.updated_at = datetime.utcnow()
            
            self.db.commit()
            
            logger.info(f"Cancelled order {order_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False
            
    def update_order_status(self, order_id: int) -> Order:
        """Update order status from broker"""
        
        order = self.db.query(Order).filter(Order.id == order_id).first()
        if not order or not order.broker_order_id:
            return order
            
        try:
            # Get latest status from broker
            broker_order = self.alpaca_service.get_order(order.broker_order_id)
            
            if broker_order:
                # Update order with latest information
                self._update_order_from_broker_data(order, broker_order)
                self.db.commit()
                
        except Exception as e:
            logger.error(f"Failed to update order {order_id} status: {e}")
            
        return order
        
    def get_user_orders(self, user_id: int, 
                       status: Optional[OrderStatus] = None,
                       symbol: Optional[str] = None,
                       limit: int = 100) -> List[Order]:
        """Get orders for a user"""
        
        query = self.db.query(Order).filter(Order.user_id == user_id)
        
        if status:
            query = query.filter(Order.status == status)
            
        if symbol:
            query = query.filter(Order.symbol == symbol)
            
        return query.order_by(Order.created_at.desc()).limit(limit).all()
        
    def get_strategy_orders(self, strategy_id: int, 
                           status: Optional[OrderStatus] = None) -> List[Order]:
        """Get orders for a strategy"""
        
        query = self.db.query(Order).filter(Order.strategy_id == strategy_id)
        
        if status:
            query = query.filter(Order.status == status)
            
        return query.order_by(Order.created_at.desc()).all()
        
    def get_open_orders(self, user_id: int) -> List[Order]:
        """Get all open orders for a user"""
        
        return self.db.query(Order).filter(
            Order.user_id == user_id,
            Order.status.in_([OrderStatus.PENDING, OrderStatus.SUBMITTED, OrderStatus.PARTIALLY_FILLED])
        ).all()
        
    def batch_update_order_statuses(self, user_id: int) -> int:
        """Update statuses for all user's orders"""
        
        open_orders = self.get_open_orders(user_id)
        updated_count = 0
        
        for order in open_orders:
            try:
                self.update_order_status(order.id)
                updated_count += 1
            except Exception as e:
                logger.error(f"Failed to update order {order.id}: {e}")
                
        return updated_count
        
    def _validate_order_request(self, order_request: OrderRequest):
        """Validate order request"""
        
        if order_request.quantity <= 0:
            raise ValueError("Quantity must be positive")
            
        if order_request.order_type in [OrderType.LIMIT, OrderType.STOP_LIMIT]:
            if order_request.limit_price is None or order_request.limit_price <= 0:
                raise ValueError("Limit price required for limit orders")
                
        if order_request.order_type in [OrderType.STOP, OrderType.STOP_LIMIT]:
            if order_request.stop_price is None or order_request.stop_price <= 0:
                raise ValueError("Stop price required for stop orders")
                
        if order_request.order_type == OrderType.TRAILING_STOP:
            if not order_request.trail_percent and not order_request.trail_price:
                raise ValueError("Trail percent or trail price required for trailing stop orders")
                
    def _update_order_from_broker_data(self, order: Order, broker_data: Dict):
        """Update order with broker data"""
        
        # Map broker status to our status
        broker_status = broker_data.get("status", "")
        status_mapping = {
            "new": OrderStatus.SUBMITTED,
            "accepted": OrderStatus.SUBMITTED,
            "filled": OrderStatus.FILLED,
            "partially_filled": OrderStatus.PARTIALLY_FILLED,
            "cancelled": OrderStatus.CANCELLED,
            "rejected": OrderStatus.REJECTED,
            "expired": OrderStatus.EXPIRED
        }
        
        if broker_status in status_mapping:
            order.status = status_mapping[broker_status]
            
        # Update fill information
        if "filled_qty" in broker_data:
            order.filled_quantity = float(broker_data["filled_qty"])
            
        if "filled_avg_price" in broker_data:
            order.average_fill_price = float(broker_data["filled_avg_price"])
            
        if "commission" in broker_data:
            order.commission = float(broker_data["commission"])
            
        # Update timestamps
        if broker_data.get("filled_at") and order.status == OrderStatus.FILLED:
            order.filled_at = datetime.fromisoformat(broker_data["filled_at"].replace("Z", "+00:00"))
            
        order.updated_at = datetime.utcnow()
        order.broker_data = json.dumps(broker_data)
        
    def get_order_performance(self, user_id: int, days: int = 30) -> Dict:
        """Get order performance metrics"""
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        orders = self.db.query(Order).filter(
            Order.user_id == user_id,
            Order.created_at >= start_date
        ).all()
        
        total_orders = len(orders)
        filled_orders = len([o for o in orders if o.status == OrderStatus.FILLED])
        cancelled_orders = len([o for o in orders if o.status == OrderStatus.CANCELLED])
        rejected_orders = len([o for o in orders if o.status == OrderStatus.REJECTED])
        
        fill_rate = (filled_orders / total_orders * 100) if total_orders > 0 else 0
        
        total_commission = sum(o.commission for o in orders if o.commission)
        
        return {
            "total_orders": total_orders,
            "filled_orders": filled_orders,
            "cancelled_orders": cancelled_orders,
            "rejected_orders": rejected_orders,
            "fill_rate": fill_rate,
            "total_commission": total_commission,
            "period_days": days
        }