from datetime import datetime, timedelta
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, Enum, Numeric
from enum import Enum as PyEnum
import json
import logging
from dataclasses import dataclass

from .database import Base
from .alpaca_service import AlpacaService

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

# Valid state transitions for order management
VALID_STATUS_TRANSITIONS = {
    OrderStatus.PENDING: [OrderStatus.SUBMITTED, OrderStatus.CANCELLED, OrderStatus.REJECTED],
    OrderStatus.SUBMITTED: [OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED, OrderStatus.EXPIRED],
    OrderStatus.PARTIALLY_FILLED: [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.EXPIRED],
    OrderStatus.FILLED: [],  # Terminal state
    OrderStatus.CANCELLED: [],  # Terminal state
    OrderStatus.REJECTED: [],  # Terminal state
    OrderStatus.EXPIRED: []  # Terminal state
}

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
        self.alpaca_service = AlpacaService()
        self.max_retry_attempts = 3
        self.retry_delay = 1  # seconds
        
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
            # Submit order to Alpaca
            if self.alpaca_service.is_connected():
                broker_order = self.alpaca_service.submit_order(
                    symbol=order.symbol,
                    qty=float(order.quantity),
                    side=order.side.value,
                    order_type=order.order_type.value,
                    time_in_force=order.time_in_force.value,
                    limit_price=float(order.limit_price) if order.limit_price else None,
                    stop_price=float(order.stop_price) if order.stop_price else None,
                    trail_percent=float(order.trail_percent) if order.trail_percent else None,
                    trail_price=float(order.trail_price) if order.trail_price else None,
                    extended_hours=order.extended_hours,
                    client_order_id=order.client_order_id
                )
                
                # Update order with broker information using safe status transition
                order.broker_order_id = broker_order.get("id")
                self._update_order_status_safe(order, OrderStatus.SUBMITTED, broker_order)
                
                logger.info(f"Successfully submitted order {order_id} to Alpaca: {broker_order.get('id')}")
            else:
                # Fallback to simulation if Alpaca is not connected
                broker_order = {
                    "id": "simulated_broker_id_" + str(order_id),
                    "status": "submitted",
                    "filled_qty": 0,
                    "filled_avg_price": 0,
                    "commission": 0,
                    "filled_at": None
                }
                logger.warning(f"Alpaca not connected, simulating order submission for order {order_id}")
                
                # Update order with simulated broker information using safe status transition
                order.broker_order_id = broker_order.get("id")
                self._update_order_status_safe(order, OrderStatus.SUBMITTED, broker_order)
            
            logger.info(f"Submitted order {order_id} to broker")
            return True
            
        except Exception as e:
            self._update_order_status_safe(order, OrderStatus.REJECTED, {"error": str(e), "timestamp": datetime.utcnow().isoformat()})
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
            # Cancel order with broker
            if order.broker_order_id:
                if self.alpaca_service.is_connected():
                    success = self.alpaca_service.cancel_order(order.broker_order_id)
                    if not success:
                        logger.error(f"Failed to cancel order {order.broker_order_id} with Alpaca")
                        return False
                    logger.info(f"Successfully cancelled order {order.broker_order_id} with Alpaca")
                else:
                    logger.warning(f"Alpaca not connected, simulating order cancellation for order {order.broker_order_id}")
                    success = True
                    
            # Update order status using safe transition
            if self._update_order_status_safe(order, OrderStatus.CANCELLED):
                logger.info(f"Cancelled order {order_id}")
                return True
            else:
                logger.error(f"Failed to update status to cancelled for order {order_id}")
                return False
            
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
    
    def _validate_status_transition(self, current_status: OrderStatus, new_status: OrderStatus) -> bool:
        """Validate if status transition is allowed"""
        valid_transitions = VALID_STATUS_TRANSITIONS.get(current_status, [])
        return new_status in valid_transitions
    
    def _update_order_status_safe(self, order: Order, new_status: OrderStatus, 
                                  broker_data: Optional[Dict] = None) -> bool:
        """Safely update order status with validation"""
        if not self._validate_status_transition(order.status, new_status):
            logger.warning(f"Invalid status transition from {order.status} to {new_status} for order {order.id}")
            return False
        
        old_status = order.status
        order.status = new_status
        order.updated_at = datetime.utcnow()
        
        if broker_data:
            order.broker_data = json.dumps(broker_data)
        
        # Set specific timestamps based on new status
        if new_status == OrderStatus.SUBMITTED and not order.submitted_at:
            order.submitted_at = datetime.utcnow()
        elif new_status == OrderStatus.FILLED and not order.filled_at:
            order.filled_at = datetime.utcnow()
        
        self.db.commit()
        logger.info(f"Order {order.id} status updated from {old_status} to {new_status}")
        return True
    
    def retry_failed_orders(self, user_id: int, max_age_hours: int = 24) -> int:
        """Retry orders that failed due to temporary issues"""
        cutoff_time = datetime.utcnow() - timedelta(hours=max_age_hours)
        
        failed_orders = self.db.query(Order).filter(
            Order.user_id == user_id,
            Order.status.in_([OrderStatus.REJECTED, OrderStatus.EXPIRED]),
            Order.created_at >= cutoff_time,
            Order.broker_data.like('%"temporary"%')  # Only retry temporary failures
        ).all()
        
        retry_count = 0
        for order in failed_orders:
            try:
                # Reset to pending status for retry
                if self._update_order_status_safe(order, OrderStatus.PENDING):
                    # Clear broker data for fresh submission
                    order.broker_order_id = None
                    order.broker_data = None
                    self.db.commit()
                    
                    # Attempt resubmission
                    if self.submit_order(order.id):
                        retry_count += 1
                        logger.info(f"Successfully retried order {order.id}")
                    else:
                        logger.warning(f"Retry failed for order {order.id}")
                        
            except Exception as e:
                logger.error(f"Error retrying order {order.id}: {e}")
        
        return retry_count
    
    def expire_day_orders(self) -> int:
        """Expire day orders at market close"""
        # Get orders that should be expired (DAY orders that are still active)
        active_day_orders = self.db.query(Order).filter(
            Order.time_in_force == TimeInForce.DAY,
            Order.status.in_([OrderStatus.PENDING, OrderStatus.SUBMITTED, OrderStatus.PARTIALLY_FILLED]),
            Order.created_at < datetime.utcnow().replace(hour=20, minute=0, second=0, microsecond=0)  # After 8 PM UTC (market close)
        ).all()
        
        expired_count = 0
        for order in active_day_orders:
            try:
                # Try to cancel with broker first
                if order.broker_order_id and self.alpaca_service.is_connected():
                    self.alpaca_service.cancel_order(order.broker_order_id)
                
                # Update status to expired
                if self._update_order_status_safe(order, OrderStatus.EXPIRED):
                    expired_count += 1
                    logger.info(f"Expired day order {order.id}")
                    
            except Exception as e:
                logger.error(f"Error expiring order {order.id}: {e}")
        
        return expired_count
    
    def get_order_statistics(self, user_id: int, days: int = 30) -> Dict:
        """Get comprehensive order statistics"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        orders = self.db.query(Order).filter(
            Order.user_id == user_id,
            Order.created_at >= start_date
        ).all()
        
        if not orders:
            return {
                "total_orders": 0,
                "period_days": days,
                "status_breakdown": {},
                "fill_rate": 0,
                "average_fill_time": None,
                "total_commission": 0,
                "total_volume": 0,
                "success_rate": 0
            }
        
        # Status breakdown
        status_counts = {}
        for status in OrderStatus:
            status_counts[status.value] = len([o for o in orders if o.status == status])
        
        # Fill rate calculation
        filled_orders = [o for o in orders if o.status == OrderStatus.FILLED]
        total_orders = len(orders)
        fill_rate = (len(filled_orders) / total_orders * 100) if total_orders > 0 else 0
        
        # Average fill time (for filled orders)
        fill_times = []
        for order in filled_orders:
            if order.submitted_at and order.filled_at:
                fill_time = (order.filled_at - order.submitted_at).total_seconds()
                fill_times.append(fill_time)
        
        avg_fill_time = sum(fill_times) / len(fill_times) if fill_times else None
        
        # Commission and volume
        total_commission = sum(o.commission for o in orders if o.commission)
        total_volume = sum(float(o.quantity) * float(o.average_fill_price or 0) for o in filled_orders)
        
        # Success rate (submitted orders that didn't get rejected)
        submitted_orders = [o for o in orders if o.status != OrderStatus.PENDING]
        rejected_orders = [o for o in orders if o.status == OrderStatus.REJECTED]
        success_rate = ((len(submitted_orders) - len(rejected_orders)) / len(submitted_orders) * 100) if submitted_orders else 0
        
        return {
            "total_orders": total_orders,
            "period_days": days,
            "status_breakdown": status_counts,
            "fill_rate": fill_rate,
            "average_fill_time_seconds": avg_fill_time,
            "total_commission": float(total_commission),
            "total_volume": total_volume,
            "success_rate": success_rate,
            "filled_orders": len(filled_orders),
            "rejected_orders": len(rejected_orders),
            "expired_orders": status_counts.get("expired", 0),
            "cancelled_orders": status_counts.get("cancelled", 0)
        }
        
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