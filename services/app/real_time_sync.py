"""Real-time data synchronization service"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Set, Any
from dataclasses import dataclass
from enum import Enum
import threading
from collections import defaultdict

from .database import get_db, Account, Holding
from .market_data import market_data_manager
from .unified_accounts import UnifiedAccountManager

logger = logging.getLogger(__name__)

class SyncEventType(Enum):
    ACCOUNT_UPDATE = "account_update"
    HOLDING_UPDATE = "holding_update"
    PRICE_UPDATE = "price_update"
    PORTFOLIO_VALUE_UPDATE = "portfolio_value_update"
    TRANSACTION_UPDATE = "transaction_update"
    SYNC_STATUS_UPDATE = "sync_status_update"

@dataclass
class SyncEvent:
    """Real-time synchronization event"""
    event_type: SyncEventType
    user_id: int
    timestamp: datetime
    data: Dict[str, Any]
    account_id: Optional[int] = None
    symbol: Optional[str] = None

@dataclass
class WebSocketConnection:
    """WebSocket connection information"""
    websocket: Any
    user_id: int
    subscriptions: Set[str]
    last_heartbeat: datetime

class RealTimeSyncManager:
    """Manager for real-time data synchronization"""
    
    def __init__(self):
        self.connections: Dict[str, WebSocketConnection] = {}
        self.user_subscriptions: Dict[int, Set[str]] = defaultdict(set)
        self.price_subscribers: Dict[str, Set[int]] = defaultdict(set)
        self.sync_thread = None
        self.is_running = False
        
    def start(self):
        """Start the real-time sync manager"""
        if self.is_running:
            return
            
        self.is_running = True
        self.sync_thread = threading.Thread(target=self._sync_loop, daemon=True)
        self.sync_thread.start()
        logger.info("Real-time sync manager started")
        
    def stop(self):
        """Stop the real-time sync manager"""
        self.is_running = False
        if self.sync_thread:
            self.sync_thread.join()
        logger.info("Real-time sync manager stopped")
        
    async def add_connection(self, websocket, user_id: int, connection_id: str):
        """Add a new WebSocket connection"""
        connection = WebSocketConnection(
            websocket=websocket,
            user_id=user_id,
            subscriptions=set(),
            last_heartbeat=datetime.utcnow()
        )
        
        self.connections[connection_id] = connection
        
        # Auto-subscribe to user's portfolio updates
        await self.subscribe_user_updates(connection_id, user_id)
        
        logger.info(f"Added WebSocket connection for user {user_id}")
        
    async def remove_connection(self, connection_id: str):
        """Remove a WebSocket connection"""
        if connection_id in self.connections:
            connection = self.connections[connection_id]
            
            # Remove from all subscriptions
            for subscription in connection.subscriptions:
                if subscription.startswith("price_"):
                    symbol = subscription.replace("price_", "")
                    self.price_subscribers[symbol].discard(connection.user_id)
                    
            self.user_subscriptions[connection.user_id].discard(connection_id)
            del self.connections[connection_id]
            
            logger.info(f"Removed WebSocket connection {connection_id}")
            
    async def subscribe_user_updates(self, connection_id: str, user_id: int):
        """Subscribe to user portfolio updates"""
        if connection_id not in self.connections:
            return
            
        connection = self.connections[connection_id]
        
        # Subscribe to general user updates
        subscription = f"user_{user_id}"
        connection.subscriptions.add(subscription)
        self.user_subscriptions[user_id].add(connection_id)
        
        # Subscribe to price updates for user's holdings
        db = next(get_db())
        try:
            holdings = db.query(Holding).join(Account).filter(
                Account.user_id == user_id
            ).all()
            
            for holding in holdings:
                if holding.symbol:
                    price_subscription = f"price_{holding.symbol}"
                    connection.subscriptions.add(price_subscription)
                    self.price_subscribers[holding.symbol].add(user_id)
                    
                    # Subscribe to market data for this symbol
                    market_data_manager.subscribe(
                        holding.symbol, 
                        lambda quote, sym=holding.symbol: self._on_price_update(sym, quote)
                    )
        finally:
            db.close()
            
    async def subscribe_symbol_updates(self, connection_id: str, symbol: str):
        """Subscribe to specific symbol price updates"""
        if connection_id not in self.connections:
            return
            
        connection = self.connections[connection_id]
        subscription = f"price_{symbol}"
        
        if subscription not in connection.subscriptions:
            connection.subscriptions.add(subscription)
            self.price_subscribers[symbol].add(connection.user_id)
            
            # Subscribe to market data
            market_data_manager.subscribe(
                symbol, 
                lambda quote: self._on_price_update(symbol, quote)
            )
            
    async def broadcast_event(self, event: SyncEvent):
        """Broadcast event to relevant connections"""
        connections_to_notify = set()
        
        # Find connections that should receive this event
        if event.user_id in self.user_subscriptions:
            connections_to_notify.update(self.user_subscriptions[event.user_id])
            
        # For price updates, notify all subscribers to that symbol
        if event.event_type == SyncEventType.PRICE_UPDATE and event.symbol:
            for user_id in self.price_subscribers.get(event.symbol, set()):
                if user_id in self.user_subscriptions:
                    connections_to_notify.update(self.user_subscriptions[user_id])
                    
        # Send event to connections
        event_data = {
            "type": event.event_type.value,
            "user_id": event.user_id,
            "timestamp": event.timestamp.isoformat(),
            "data": event.data
        }
        
        if event.account_id:
            event_data["account_id"] = event.account_id
        if event.symbol:
            event_data["symbol"] = event.symbol
            
        message = json.dumps(event_data)
        
        # Send to all relevant connections
        for connection_id in connections_to_notify:
            if connection_id in self.connections:
                try:
                    await self.connections[connection_id].websocket.send_text(message)
                except Exception as e:
                    logger.error(f"Failed to send message to connection {connection_id}: {e}")
                    # Remove failed connection
                    await self.remove_connection(connection_id)
                    
    def _sync_loop(self):
        """Main synchronization loop"""
        while self.is_running:
            try:
                # Periodic portfolio value updates
                self._update_portfolio_values()
                
                # Cleanup stale connections
                self._cleanup_stale_connections()
                
                # Sleep for a bit
                threading.Event().wait(30)  # Update every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in sync loop: {e}")
                threading.Event().wait(60)  # Wait longer on error
                
    def _update_portfolio_values(self):
        """Update portfolio values for active users"""
        active_users = set()
        
        # Get all users with active connections
        for connection in self.connections.values():
            active_users.add(connection.user_id)
            
        db = next(get_db())
        try:
            for user_id in active_users:
                try:
                    manager = UnifiedAccountManager(db)
                    summary = manager.get_account_summary(user_id)
                    
                    # Create portfolio value update event
                    event = SyncEvent(
                        event_type=SyncEventType.PORTFOLIO_VALUE_UPDATE,
                        user_id=user_id,
                        timestamp=datetime.utcnow(),
                        data={
                            "total_value": summary.total_value,
                            "total_cash": summary.total_cash,
                            "total_investments": summary.total_investments,
                            "last_sync": summary.last_sync.isoformat() if summary.last_sync else None
                        }
                    )
                    
                    # Use asyncio to broadcast the event
                    asyncio.create_task(self.broadcast_event(event))
                    
                except Exception as e:
                    logger.error(f"Failed to update portfolio value for user {user_id}: {e}")
                    
        finally:
            db.close()
            
    def _on_price_update(self, symbol: str, quote):
        """Handle price update from market data"""
        # Create price update event for all users subscribed to this symbol
        for user_id in self.price_subscribers.get(symbol, set()):
            event = SyncEvent(
                event_type=SyncEventType.PRICE_UPDATE,
                user_id=user_id,
                timestamp=datetime.utcnow(),
                symbol=symbol,
                data={
                    "symbol": symbol,
                    "price": quote.last_price,
                    "change": quote.change,
                    "change_percent": quote.change_percent,
                    "volume": quote.volume
                }
            )
            
            asyncio.create_task(self.broadcast_event(event))
            
    def _cleanup_stale_connections(self):
        """Remove connections that haven't sent heartbeat recently"""
        stale_threshold = datetime.utcnow() - timedelta(minutes=5)
        stale_connections = []
        
        for connection_id, connection in self.connections.items():
            if connection.last_heartbeat < stale_threshold:
                stale_connections.append(connection_id)
                
        for connection_id in stale_connections:
            asyncio.create_task(self.remove_connection(connection_id))
            
    async def update_heartbeat(self, connection_id: str):
        """Update heartbeat for a connection"""
        if connection_id in self.connections:
            self.connections[connection_id].last_heartbeat = datetime.utcnow()
            
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        active_users = set()
        total_subscriptions = 0
        
        for connection in self.connections.values():
            active_users.add(connection.user_id)
            total_subscriptions += len(connection.subscriptions)
            
        return {
            "total_connections": len(self.connections),
            "active_users": len(active_users),
            "total_subscriptions": total_subscriptions,
            "price_subscriptions": len(self.price_subscribers)
        }

# Global sync manager instance
real_time_sync_manager = RealTimeSyncManager()

def start_real_time_sync():
    """Start the global real-time sync manager"""
    real_time_sync_manager.start()
    
def stop_real_time_sync():
    """Stop the global real-time sync manager"""
    real_time_sync_manager.stop()

class SyncEventPublisher:
    """Publisher for sync events"""
    
    @staticmethod
    async def publish_account_update(user_id: int, account_id: int, data: Dict[str, Any]):
        """Publish account update event"""
        event = SyncEvent(
            event_type=SyncEventType.ACCOUNT_UPDATE,
            user_id=user_id,
            account_id=account_id,
            timestamp=datetime.utcnow(),
            data=data
        )
        await real_time_sync_manager.broadcast_event(event)
        
    @staticmethod
    async def publish_holding_update(user_id: int, account_id: int, symbol: str, data: Dict[str, Any]):
        """Publish holding update event"""
        event = SyncEvent(
            event_type=SyncEventType.HOLDING_UPDATE,
            user_id=user_id,
            account_id=account_id,
            symbol=symbol,
            timestamp=datetime.utcnow(),
            data=data
        )
        await real_time_sync_manager.broadcast_event(event)
        
    @staticmethod
    async def publish_transaction_update(user_id: int, data: Dict[str, Any]):
        """Publish transaction update event"""
        event = SyncEvent(
            event_type=SyncEventType.TRANSACTION_UPDATE,
            user_id=user_id,
            timestamp=datetime.utcnow(),
            data=data
        )
        await real_time_sync_manager.broadcast_event(event)
        
    @staticmethod
    async def publish_sync_status_update(user_id: int, status: str, message: str):
        """Publish sync status update"""
        event = SyncEvent(
            event_type=SyncEventType.SYNC_STATUS_UPDATE,
            user_id=user_id,
            timestamp=datetime.utcnow(),
            data={
                "status": status,
                "message": message
            }
        )
        await real_time_sync_manager.broadcast_event(event)