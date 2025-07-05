from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

from .database import get_db
from .order_management import (
    OrderManagementSystem, 
    OrderRequest, 
    OrderType, 
    OrderSide, 
    OrderStatus, 
    TimeInForce
)

router = APIRouter(prefix="/orders", tags=["orders"])


class OrderRequestModel(BaseModel):
    """Pydantic model for order requests"""
    symbol: str
    side: str  # "buy" or "sell"
    quantity: float
    order_type: str  # "market", "limit", "stop", "stop_limit", "trailing_stop"
    time_in_force: str = "day"  # "day", "gtc", "ioc", "fok"
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    trail_percent: Optional[float] = None
    trail_price: Optional[float] = None
    extended_hours: bool = False
    client_order_id: Optional[str] = None
    account_id: Optional[int] = None
    strategy_id: Optional[int] = None


class OrderResponse(BaseModel):
    """Order response model"""
    id: int
    user_id: int
    symbol: str
    side: str
    quantity: float
    order_type: str
    status: str
    created_at: datetime
    updated_at: datetime
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    filled_quantity: Optional[float] = None
    average_fill_price: Optional[float] = None
    commission: Optional[float] = None
    broker_order_id: Optional[str] = None


class OrderPerformanceResponse(BaseModel):
    """Order performance response model"""
    total_orders: int
    filled_orders: int
    cancelled_orders: int
    rejected_orders: int
    fill_rate: float
    total_commission: float
    period_days: int


@router.post("/create/{user_id}", response_model=OrderResponse)
async def create_order(
    user_id: int,
    order_request: OrderRequestModel,
    db: Session = Depends(get_db)
):
    """Create a new order"""
    
    oms = OrderManagementSystem(db)
    
    try:
        # Convert string enums to proper types
        order_req = OrderRequest(
            symbol=order_request.symbol.upper(),
            side=OrderSide(order_request.side.lower()),
            quantity=order_request.quantity,
            order_type=OrderType(order_request.order_type.lower()),
            time_in_force=TimeInForce(order_request.time_in_force.lower()),
            limit_price=order_request.limit_price,
            stop_price=order_request.stop_price,
            trail_percent=order_request.trail_percent,
            trail_price=order_request.trail_price,
            extended_hours=order_request.extended_hours,
            client_order_id=order_request.client_order_id
        )
        
        order = oms.create_order(
            user_id=user_id,
            order_request=order_req,
            account_id=order_request.account_id,
            strategy_id=order_request.strategy_id
        )
        
        return OrderResponse(
            id=order.id,
            user_id=order.user_id,
            symbol=order.symbol,
            side=order.side.value,
            quantity=order.quantity,
            order_type=order.order_type.value,
            status=order.status.value,
            created_at=order.created_at,
            updated_at=order.updated_at,
            limit_price=order.limit_price,
            stop_price=order.stop_price,
            filled_quantity=order.filled_quantity,
            average_fill_price=order.average_fill_price,
            commission=order.commission,
            broker_order_id=order.broker_order_id
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/submit/{order_id}")
async def submit_order(
    order_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Submit an order to the broker"""
    
    oms = OrderManagementSystem(db)
    
    try:
        success = oms.submit_order(order_id)
        
        if success:
            # Schedule status update in background
            background_tasks.add_task(oms.update_order_status, order_id)
            return {"message": "Order submitted successfully", "order_id": order_id}
        else:
            raise HTTPException(status_code=400, detail="Failed to submit order")
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/cancel/{order_id}")
async def cancel_order(
    order_id: int,
    db: Session = Depends(get_db)
):
    """Cancel an order"""
    
    oms = OrderManagementSystem(db)
    
    try:
        success = oms.cancel_order(order_id)
        
        if success:
            return {"message": "Order cancelled successfully", "order_id": order_id}
        else:
            raise HTTPException(status_code=400, detail="Failed to cancel order")
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/user/{user_id}", response_model=List[OrderResponse])
async def get_user_orders(
    user_id: int,
    status: Optional[str] = None,
    symbol: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get orders for a user"""
    
    oms = OrderManagementSystem(db)
    
    try:
        order_status = OrderStatus(status.lower()) if status else None
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    orders = oms.get_user_orders(
        user_id=user_id,
        status=order_status,
        symbol=symbol.upper() if symbol else None,
        limit=limit
    )
    
    return [
        OrderResponse(
            id=order.id,
            user_id=order.user_id,
            symbol=order.symbol,
            side=order.side.value,
            quantity=order.quantity,
            order_type=order.order_type.value,
            status=order.status.value,
            created_at=order.created_at,
            updated_at=order.updated_at,
            limit_price=order.limit_price,
            stop_price=order.stop_price,
            filled_quantity=order.filled_quantity,
            average_fill_price=order.average_fill_price,
            commission=order.commission,
            broker_order_id=order.broker_order_id
        )
        for order in orders
    ]


@router.get("/strategy/{strategy_id}", response_model=List[OrderResponse])
async def get_strategy_orders(
    strategy_id: int,
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get orders for a strategy"""
    
    oms = OrderManagementSystem(db)
    
    try:
        order_status = OrderStatus(status.lower()) if status else None
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    orders = oms.get_strategy_orders(
        strategy_id=strategy_id,
        status=order_status
    )
    
    return [
        OrderResponse(
            id=order.id,
            user_id=order.user_id,
            symbol=order.symbol,
            side=order.side.value,
            quantity=order.quantity,
            order_type=order.order_type.value,
            status=order.status.value,
            created_at=order.created_at,
            updated_at=order.updated_at,
            limit_price=order.limit_price,
            stop_price=order.stop_price,
            filled_quantity=order.filled_quantity,
            average_fill_price=order.average_fill_price,
            commission=order.commission,
            broker_order_id=order.broker_order_id
        )
        for order in orders
    ]


@router.get("/open/{user_id}", response_model=List[OrderResponse])
async def get_open_orders(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Get all open orders for a user"""
    
    oms = OrderManagementSystem(db)
    orders = oms.get_open_orders(user_id)
    
    return [
        OrderResponse(
            id=order.id,
            user_id=order.user_id,
            symbol=order.symbol,
            side=order.side.value,
            quantity=order.quantity,
            order_type=order.order_type.value,
            status=order.status.value,
            created_at=order.created_at,
            updated_at=order.updated_at,
            limit_price=order.limit_price,
            stop_price=order.stop_price,
            filled_quantity=order.filled_quantity,
            average_fill_price=order.average_fill_price,
            commission=order.commission,
            broker_order_id=order.broker_order_id
        )
        for order in orders
    ]


@router.get("/status/{order_id}", response_model=OrderResponse)
async def get_order_status(
    order_id: int,
    db: Session = Depends(get_db)
):
    """Get current order status"""
    
    oms = OrderManagementSystem(db)
    order = oms.update_order_status(order_id)
    
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return OrderResponse(
        id=order.id,
        user_id=order.user_id,
        symbol=order.symbol,
        side=order.side.value,
        quantity=order.quantity,
        order_type=order.order_type.value,
        status=order.status.value,
        created_at=order.created_at,
        updated_at=order.updated_at,
        limit_price=order.limit_price,
        stop_price=order.stop_price,
        filled_quantity=order.filled_quantity,
        average_fill_price=order.average_fill_price,
        commission=order.commission,
        broker_order_id=order.broker_order_id
    )


@router.post("/sync/{user_id}")
async def sync_user_orders(
    user_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Sync all order statuses for a user"""
    
    oms = OrderManagementSystem(db)
    
    # Schedule background task to update all orders
    background_tasks.add_task(oms.batch_update_order_statuses, user_id)
    
    return {"message": f"Order status sync queued for user {user_id}"}


@router.get("/performance/{user_id}", response_model=OrderPerformanceResponse)
async def get_order_performance(
    user_id: int,
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Get order performance metrics"""
    
    oms = OrderManagementSystem(db)
    performance = oms.get_order_performance(user_id, days)
    
    return OrderPerformanceResponse(**performance)


@router.get("/types")
async def get_order_types():
    """Get available order types and their descriptions"""
    
    return {
        "order_types": [
            {
                "type": "market",
                "name": "Market Order",
                "description": "Execute immediately at current market price"
            },
            {
                "type": "limit",
                "name": "Limit Order",
                "description": "Execute only at specified price or better"
            },
            {
                "type": "stop",
                "name": "Stop Order",
                "description": "Market order triggered when price reaches stop price"
            },
            {
                "type": "stop_limit",
                "name": "Stop Limit Order",
                "description": "Limit order triggered when price reaches stop price"
            },
            {
                "type": "trailing_stop",
                "name": "Trailing Stop Order",
                "description": "Stop order that trails the market price"
            }
        ],
        "sides": [
            {"side": "buy", "description": "Buy shares"},
            {"side": "sell", "description": "Sell shares"}
        ],
        "time_in_force": [
            {"tif": "day", "description": "Valid for current trading day"},
            {"tif": "gtc", "description": "Good till cancelled"},
            {"tif": "ioc", "description": "Immediate or cancel"},
            {"tif": "fok", "description": "Fill or kill"}
        ]
    }


@router.post("/create-and-submit/{user_id}")
async def create_and_submit_order(
    user_id: int,
    order_request: OrderRequestModel,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Create and immediately submit an order"""
    
    oms = OrderManagementSystem(db)
    
    try:
        # Convert string enums to proper types
        order_req = OrderRequest(
            symbol=order_request.symbol.upper(),
            side=OrderSide(order_request.side.lower()),
            quantity=order_request.quantity,
            order_type=OrderType(order_request.order_type.lower()),
            time_in_force=TimeInForce(order_request.time_in_force.lower()),
            limit_price=order_request.limit_price,
            stop_price=order_request.stop_price,
            trail_percent=order_request.trail_percent,
            trail_price=order_request.trail_price,
            extended_hours=order_request.extended_hours,
            client_order_id=order_request.client_order_id
        )
        
        # Create order
        order = oms.create_order(
            user_id=user_id,
            order_request=order_req,
            account_id=order_request.account_id,
            strategy_id=order_request.strategy_id
        )
        
        # Submit order
        success = oms.submit_order(order.id)
        
        if success:
            # Schedule status update in background
            background_tasks.add_task(oms.update_order_status, order.id)
            
            return {
                "message": "Order created and submitted successfully",
                "order_id": order.id,
                "broker_order_id": order.broker_order_id
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to submit order")
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))