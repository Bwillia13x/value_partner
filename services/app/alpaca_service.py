"""Alpaca trading and account management service"""
import os
import logging
from typing import Dict, List, Optional, Any
from urllib.parse import urlencode
from fastapi import HTTPException, status
from alpaca_trade_api import REST, TimeFrame
from alpaca_trade_api.rest import APIError
from datetime import datetime, timedelta
import alpaca_trade_api as tradeapi

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AlpacaService:
    def __init__(self):
        self.api_key = os.getenv("ALPACA_API_KEY")
        self.api_secret = os.getenv("ALPACA_API_SECRET")
        self.base_url = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
        
        if not self.api_key or not self.api_secret:
            logger.warning("Alpaca API credentials not found in environment variables")
            self.api = None
        else:
            try:
                self.api = REST(
                    key_id=self.api_key,
                    secret_key=self.api_secret,
                    base_url=self.base_url
                )
                logger.info("Alpaca API client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Alpaca API client: {e}")
                self.api = None
    
    def is_connected(self) -> bool:
        """Check if Alpaca API is connected"""
        if not self.api:
            return False
        try:
            account = self.api.get_account()
            return account is not None
        except Exception as e:
            logger.error(f"Alpaca connection check failed: {e}")
            return False
    
    def get_account(self) -> Optional[Dict]:
        """Get account information"""
        if not self.api:
            return None
        try:
            account = self.api.get_account()
            return {
                "id": account.id,
                "account_number": account.account_number,
                "status": account.status,
                "currency": account.currency,
                "buying_power": float(account.buying_power),
                "cash": float(account.cash),
                "portfolio_value": float(account.portfolio_value),
                "equity": float(account.equity),
                "last_equity": float(account.last_equity),
                "multiplier": int(account.multiplier),
                "day_trade_count": int(account.day_trade_count),
                "daytrade_buying_power": float(account.daytrade_buying_power),
                "regt_buying_power": float(account.regt_buying_power),
                "initial_margin": float(account.initial_margin),
                "maintenance_margin": float(account.maintenance_margin),
                "pattern_day_trader": account.pattern_day_trader,
                "trading_blocked": account.trading_blocked,
                "transfers_blocked": account.transfers_blocked,
                "account_blocked": account.account_blocked,
                "created_at": account.created_at.isoformat() if account.created_at else None,
                "trade_suspended_by_user": account.trade_suspended_by_user,
                "shorting_enabled": account.shorting_enabled,
                "long_market_value": float(account.long_market_value),
                "short_market_value": float(account.short_market_value),
            }
        except APIError as e:
            logger.error(f"Alpaca API error getting account: {e}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            logger.error(f"Error getting account: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get account")
    
    def get_positions(self) -> List[Dict]:
        """Get current positions"""
        if not self.api:
            return []
        try:
            positions = self.api.list_positions()
            return [
                {
                    "symbol": pos.symbol,
                    "quantity": float(pos.qty),
                    "side": pos.side,
                    "market_value": float(pos.market_value),
                    "cost_basis": float(pos.cost_basis),
                    "unrealized_pl": float(pos.unrealized_pl),
                    "unrealized_plpc": float(pos.unrealized_plpc),
                    "current_price": float(pos.current_price),
                    "lastday_price": float(pos.lastday_price),
                    "change_today": float(pos.change_today),
                    "avg_entry_price": float(pos.avg_entry_price),
                    "asset_id": pos.asset_id,
                    "asset_class": pos.asset_class,
                    "exchange": pos.exchange,
                }
                for pos in positions
            ]
        except APIError as e:
            logger.error(f"Alpaca API error getting positions: {e}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to get positions")
    
    def submit_order(self, symbol: str, qty: float, side: str, order_type: str = "market", 
                     time_in_force: str = "day", limit_price: Optional[float] = None,
                     stop_price: Optional[float] = None, trail_percent: Optional[float] = None,
                     trail_price: Optional[float] = None, extended_hours: bool = False,
                     client_order_id: Optional[str] = None) -> Dict:
        """Submit an order to Alpaca"""
        if not self.api:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Alpaca API not available")
        
        try:
            order = self.api.submit_order(
                symbol=symbol,
                qty=qty,
                side=side,
                type=order_type,
                time_in_force=time_in_force,
                limit_price=limit_price,
                stop_price=stop_price,
                trail_percent=trail_percent,
                trail_price=trail_price,
                extended_hours=extended_hours,
                client_order_id=client_order_id
            )
            
            return {
                "id": order.id,
                "client_order_id": order.client_order_id,
                "symbol": order.symbol,
                "qty": float(order.qty),
                "side": order.side,
                "order_type": order.order_type,
                "time_in_force": order.time_in_force,
                "limit_price": float(order.limit_price) if order.limit_price else None,
                "stop_price": float(order.stop_price) if order.stop_price else None,
                "trail_percent": float(order.trail_percent) if order.trail_percent else None,
                "trail_price": float(order.trail_price) if order.trail_price else None,
                "status": order.status,
                "created_at": order.created_at.isoformat() if order.created_at else None,
                "updated_at": order.updated_at.isoformat() if order.updated_at else None,
                "submitted_at": order.submitted_at.isoformat() if order.submitted_at else None,
                "filled_at": order.filled_at.isoformat() if order.filled_at else None,
                "expired_at": order.expired_at.isoformat() if order.expired_at else None,
                "canceled_at": order.canceled_at.isoformat() if order.canceled_at else None,
                "failed_at": order.failed_at.isoformat() if order.failed_at else None,
                "replaced_at": order.replaced_at.isoformat() if order.replaced_at else None,
                "replaced_by": order.replaced_by,
                "replaces": order.replaces,
                "asset_id": order.asset_id,
                "asset_class": order.asset_class,
                "notional": float(order.notional) if order.notional else None,
                "qty": float(order.qty) if order.qty else None,
                "filled_qty": float(order.filled_qty) if order.filled_qty else None,
                "filled_avg_price": float(order.filled_avg_price) if order.filled_avg_price else None,
                "order_class": order.order_class,
                "order_type": order.order_type,
                "type": order.type,
                "side": order.side,
                "amount": float(order.amount) if order.amount else None,
                "hwm": float(order.hwm) if order.hwm else None,
                "commission": float(order.commission) if order.commission else None,
                "extended_hours": order.extended_hours,
            }
        except APIError as e:
            logger.error(f"Alpaca API error submitting order: {e}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
        except Exception as e:
            logger.error(f"Error submitting order: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to submit order")
    
    def get_order(self, order_id: str) -> Optional[Dict]:
        """Get order by ID"""
        if not self.api:
            return None
        try:
            order = self.api.get_order(order_id)
            return {
                "id": order.id,
                "client_order_id": order.client_order_id,
                "symbol": order.symbol,
                "qty": float(order.qty) if order.qty else None,
                "side": order.side,
                "order_type": order.order_type,
                "time_in_force": order.time_in_force,
                "limit_price": float(order.limit_price) if order.limit_price else None,
                "stop_price": float(order.stop_price) if order.stop_price else None,
                "status": order.status,
                "created_at": order.created_at.isoformat() if order.created_at else None,
                "updated_at": order.updated_at.isoformat() if order.updated_at else None,
                "submitted_at": order.submitted_at.isoformat() if order.submitted_at else None,
                "filled_at": order.filled_at.isoformat() if order.filled_at else None,
                "filled_qty": float(order.filled_qty) if order.filled_qty else None,
                "filled_avg_price": float(order.filled_avg_price) if order.filled_avg_price else None,
                "commission": float(order.commission) if order.commission else None,
                "extended_hours": order.extended_hours,
            }
        except APIError as e:
            logger.error(f"Alpaca API error getting order: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting order: {e}")
            return None
    
    def cancel_order(self, order_id: str) -> bool:
        """Cancel an order"""
        if not self.api:
            return False
        try:
            self.api.cancel_order(order_id)
            return True
        except APIError as e:
            logger.error(f"Alpaca API error canceling order: {e}")
            return False
        except Exception as e:
            logger.error(f"Error canceling order: {e}")
            return False
    
    def get_orders(self, status: Optional[str] = None, limit: int = 100, 
                   after: Optional[datetime] = None, until: Optional[datetime] = None,
                   direction: str = "desc", nested: bool = True) -> List[Dict]:
        """Get orders"""
        if not self.api:
            return []
        try:
            orders = self.api.list_orders(
                status=status,
                limit=limit,
                after=after,
                until=until,
                direction=direction,
                nested=nested
            )
            return [
                {
                    "id": order.id,
                    "client_order_id": order.client_order_id,
                    "symbol": order.symbol,
                    "qty": float(order.qty) if order.qty else None,
                    "side": order.side,
                    "order_type": order.order_type,
                    "time_in_force": order.time_in_force,
                    "limit_price": float(order.limit_price) if order.limit_price else None,
                    "stop_price": float(order.stop_price) if order.stop_price else None,
                    "status": order.status,
                    "created_at": order.created_at.isoformat() if order.created_at else None,
                    "updated_at": order.updated_at.isoformat() if order.updated_at else None,
                    "submitted_at": order.submitted_at.isoformat() if order.submitted_at else None,
                    "filled_at": order.filled_at.isoformat() if order.filled_at else None,
                    "filled_qty": float(order.filled_qty) if order.filled_qty else None,
                    "filled_avg_price": float(order.filled_avg_price) if order.filled_avg_price else None,
                    "commission": float(order.commission) if order.commission else None,
                    "extended_hours": order.extended_hours,
                }
                for order in orders
            ]
        except APIError as e:
            logger.error(f"Alpaca API error getting orders: {e}")
            return []
        except Exception as e:
            logger.error(f"Error getting orders: {e}")
            return []

def execute_trade(symbol: str, quantity: float, action: str):
    """Legacy function for backward compatibility"""
    service = AlpacaService()
    if not service.is_connected():
        logger.warning("Alpaca not connected, simulating trade")
        return {"symbol": symbol, "quantity": quantity, "action": action, "status": "simulated"}
    
    try:
        result = service.submit_order(
            symbol=symbol,
            qty=quantity,
            side=action.lower(),
            order_type="market"
        )
        return {"symbol": symbol, "quantity": quantity, "action": action, "status": "submitted", "order_id": result["id"]}
    except Exception as e:
        logger.error(f"Failed to execute trade: {e}")
        return {"symbol": symbol, "quantity": quantity, "action": action, "status": "failed", "error": str(e)}

