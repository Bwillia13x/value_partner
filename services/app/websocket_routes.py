"""WebSocket routes for real-time data streaming"""
import uuid
import json
import logging
from datetime import datetime
from typing import Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.security import HTTPBearer

from .auth import verify_token, get_current_user
from .real_time_sync import real_time_sync_manager, SyncEventPublisher
from .monitoring import track_operation, app_monitor

logger = logging.getLogger(__name__)
security = HTTPBearer()

router = APIRouter(prefix="/ws", tags=["websocket"])

class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_connections: Dict[int, set] = {}
        
    async def connect(self, websocket: WebSocket, user_id: int) -> str:
        """Accept a new WebSocket connection"""
        await websocket.accept()
        
        connection_id = str(uuid.uuid4())
        self.active_connections[connection_id] = websocket
        
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(connection_id)
        
        # Add to real-time sync manager
        await real_time_sync_manager.add_connection(websocket, user_id, connection_id)
        
        # Track connection in monitoring
        app_monitor.track_request("/ws/connect", "WEBSOCKET", 200, 0)
        
        logger.info(f"WebSocket connection established: {connection_id} for user {user_id}")
        return connection_id
        
    async def disconnect(self, connection_id: str, user_id: int):
        """Remove a WebSocket connection"""
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
            
        if user_id in self.user_connections:
            self.user_connections[user_id].discard(connection_id)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
                
        # Remove from real-time sync manager
        await real_time_sync_manager.remove_connection(connection_id)
        
        logger.info(f"WebSocket connection closed: {connection_id}")
        
    async def send_personal_message(self, message: str, connection_id: str):
        """Send a message to a specific connection"""
        if connection_id in self.active_connections:
            try:
                await self.active_connections[connection_id].send_text(message)
            except Exception as e:
                logger.error(f"Failed to send message to {connection_id}: {e}")
                # Connection might be dead, will be cleaned up elsewhere
                
    async def broadcast_to_user(self, message: str, user_id: int):
        """Send a message to all connections for a specific user"""
        if user_id in self.user_connections:
            for connection_id in self.user_connections[user_id].copy():
                await self.send_personal_message(message, connection_id)
                
    def get_connection_count(self) -> int:
        """Get total number of active connections"""
        return len(self.active_connections)
        
    def get_user_connection_count(self, user_id: int) -> int:
        """Get number of connections for a specific user"""
        return len(self.user_connections.get(user_id, set()))

# Global connection manager
connection_manager = ConnectionManager()

async def authenticate_websocket_token(token: str) -> Dict[str, Any]:
    """Authenticate WebSocket connection using JWT token"""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required"
        )
    
    # Verify token
    payload = verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    return payload

@router.websocket("/portfolio")
async def portfolio_websocket(websocket: WebSocket, token: str = None):
    """WebSocket endpoint for real-time portfolio updates"""
    
    if not token:
        await websocket.close(code=4001, reason="Authentication token required")
        return
    
    try:
        # Authenticate user
        payload = await authenticate_websocket_token(token)
        user_id = payload.get("sub")
        
        if not user_id:
            await websocket.close(code=4001, reason="Invalid token payload")
            return
            
        # For WebSocket auth, we need to validate the user exists
        from .database import get_db
        db = next(get_db())
        try:
            from .models import User
            user = db.query(User).filter(
                (User.username == user_id) | (User.email == user_id)
            ).first()
            
            if not user:
                await websocket.close(code=4001, reason="User not found")
                return
                
            actual_user_id = user.id
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"WebSocket authentication failed: {e}")
        await websocket.close(code=4001, reason="Authentication failed")
        return
    
    # Establish connection
    connection_id = await connection_manager.connect(websocket, actual_user_id)
    
    try:
        # Send welcome message
        welcome_message = {
            "type": "connection_established",
            "connection_id": connection_id,
            "user_id": actual_user_id,
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Connected to real-time portfolio updates"
        }
        await websocket.send_text(json.dumps(welcome_message))
        
        # Main message loop
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_text()
                message = json.loads(data)
                
                # Handle different message types
                await handle_websocket_message(
                    websocket, connection_id, actual_user_id, message
                )
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected: {connection_id}")
                break
            except json.JSONDecodeError:
                error_message = {
                    "type": "error",
                    "message": "Invalid JSON format",
                    "timestamp": datetime.utcnow().isoformat()
                }
                await websocket.send_text(json.dumps(error_message))
            except Exception as e:
                logger.error(f"Error in WebSocket message handling: {e}")
                error_message = {
                    "type": "error",
                    "message": "Internal server error",
                    "timestamp": datetime.utcnow().isoformat()
                }
                await websocket.send_text(json.dumps(error_message))
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"Unexpected error in WebSocket connection: {e}")
    finally:
        await connection_manager.disconnect(connection_id, actual_user_id)

async def handle_websocket_message(
    websocket: WebSocket, 
    connection_id: str, 
    user_id: int, 
    message: Dict[str, Any]
):
    """Handle incoming WebSocket messages"""
    
    message_type = message.get("type")
    
    if message_type == "heartbeat":
        # Update heartbeat
        await real_time_sync_manager.update_heartbeat(connection_id)
        
        # Send heartbeat response
        response = {
            "type": "heartbeat_ack",
            "timestamp": datetime.utcnow().isoformat()
        }
        await websocket.send_text(json.dumps(response))
        
    elif message_type == "subscribe_symbol":
        # Subscribe to specific symbol updates
        symbol = message.get("symbol")
        if symbol:
            await real_time_sync_manager.subscribe_symbol_updates(connection_id, symbol)
            
            response = {
                "type": "subscription_confirmed",
                "symbol": symbol,
                "timestamp": datetime.utcnow().isoformat()
            }
            await websocket.send_text(json.dumps(response))
        else:
            error_response = {
                "type": "error",
                "message": "Symbol parameter required for subscription",
                "timestamp": datetime.utcnow().isoformat()
            }
            await websocket.send_text(json.dumps(error_response))
            
    elif message_type == "get_portfolio_summary":
        # Send current portfolio summary
        try:
            from .database import get_db
            from .unified_accounts import UnifiedAccountManager
            
            db = next(get_db())
            try:
                manager = UnifiedAccountManager(db)
                summary = manager.get_account_summary(user_id)
                
                response = {
                    "type": "portfolio_summary",
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": {
                        "total_value": float(summary.total_value) if summary.total_value else 0,
                        "total_cash": float(summary.total_cash) if summary.total_cash else 0,
                        "total_investments": float(summary.total_investments) if summary.total_investments else 0,
                        "account_count": summary.account_count,
                        "last_sync": summary.last_sync.isoformat() if summary.last_sync else None
                    }
                }
                await websocket.send_text(json.dumps(response))
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error getting portfolio summary: {e}")
            error_response = {
                "type": "error",
                "message": "Failed to get portfolio summary",
                "timestamp": datetime.utcnow().isoformat()
            }
            await websocket.send_text(json.dumps(error_response))
            
    elif message_type == "get_connection_stats":
        # Send connection statistics (for debugging)
        stats = real_time_sync_manager.get_connection_stats()
        response = {
            "type": "connection_stats",
            "timestamp": datetime.utcnow().isoformat(),
            "data": stats
        }
        await websocket.send_text(json.dumps(response))
        
    else:
        # Unknown message type
        error_response = {
            "type": "error",
            "message": f"Unknown message type: {message_type}",
            "timestamp": datetime.utcnow().isoformat()
        }
        await websocket.send_text(json.dumps(error_response))

@router.websocket("/market_data")
async def market_data_websocket(websocket: WebSocket, token: str = None, symbols: str = None):
    """WebSocket endpoint for real-time market data"""
    
    if not token:
        await websocket.close(code=4001, reason="Authentication token required")
        return
    
    try:
        # Authenticate user
        payload = await authenticate_websocket_token(token)
        user_id = payload.get("sub")
        
        if not user_id:
            await websocket.close(code=4001, reason="Invalid token payload")
            return
            
        # Parse symbols parameter
        symbol_list = []
        if symbols:
            symbol_list = [s.strip().upper() for s in symbols.split(",")]
            
    except Exception as e:
        logger.error(f"Market data WebSocket authentication failed: {e}")
        await websocket.close(code=4001, reason="Authentication failed")
        return
    
    # Establish connection  
    connection_id = await connection_manager.connect(websocket, hash(user_id))  # Use hash for market data connections
    
    try:
        # Subscribe to requested symbols
        for symbol in symbol_list:
            await real_time_sync_manager.subscribe_symbol_updates(connection_id, symbol)
            
        # Send welcome message
        welcome_message = {
            "type": "market_data_connected",
            "connection_id": connection_id,
            "subscribed_symbols": symbol_list,
            "timestamp": datetime.utcnow().isoformat()
        }
        await websocket.send_text(json.dumps(welcome_message))
        
        # Main message loop for market data
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                if message.get("type") == "subscribe":
                    new_symbol = message.get("symbol", "").strip().upper()
                    if new_symbol:
                        await real_time_sync_manager.subscribe_symbol_updates(connection_id, new_symbol)
                        response = {
                            "type": "subscribed",
                            "symbol": new_symbol,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        await websocket.send_text(json.dumps(response))
                        
                elif message.get("type") == "heartbeat":
                    await real_time_sync_manager.update_heartbeat(connection_id)
                    response = {
                        "type": "heartbeat_ack",
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    await websocket.send_text(json.dumps(response))
                    
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error in market data WebSocket: {e}")
                
    except WebSocketDisconnect:
        logger.info(f"Market data WebSocket disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"Unexpected error in market data WebSocket: {e}")
    finally:
        await connection_manager.disconnect(connection_id, hash(user_id))

# HTTP endpoints for WebSocket information
@router.get("/connections")
async def get_connection_info(current_user = Depends(get_current_user)):
    """Get WebSocket connection information"""
    
    user_connections = connection_manager.get_user_connection_count(current_user.id)
    total_connections = connection_manager.get_connection_count()
    sync_stats = real_time_sync_manager.get_connection_stats()
    
    return {
        "user_connections": user_connections,
        "total_connections": total_connections,
        "sync_statistics": sync_stats,
        "timestamp": datetime.utcnow().isoformat()
    }

@router.post("/broadcast")
async def broadcast_message(
    message: Dict[str, Any],
    target_user_id: int = None,
    current_user = Depends(get_current_user)
):
    """Broadcast a message to WebSocket connections (admin only)"""
    
    # For now, only allow users to broadcast to themselves
    # In production, add proper admin role checking
    if target_user_id and target_user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Can only broadcast to your own connections"
        )
    
    target_id = target_user_id or current_user.id
    
    broadcast_message = {
        "type": "broadcast",
        "timestamp": datetime.utcnow().isoformat(),
        "data": message
    }
    
    await connection_manager.broadcast_to_user(
        json.dumps(broadcast_message), 
        target_id
    )
    
    return {
        "message": "Broadcast sent successfully",
        "target_user_id": target_id,
        "timestamp": datetime.utcnow().isoformat()
    }

@router.post("/trigger_sync")
async def trigger_portfolio_sync(current_user = Depends(get_current_user)):
    """Trigger a portfolio synchronization for the current user"""
    
    try:
        # Publish sync status update
        await SyncEventPublisher.publish_sync_status_update(
            user_id=current_user.id,
            status="syncing",
            message="Portfolio synchronization started"
        )
        
        # Here you would trigger actual sync process
        # For now, we'll just simulate it
        from .database import get_db
        from .unified_accounts import UnifiedAccountManager
        
        db = next(get_db())
        try:
            manager = UnifiedAccountManager(db)
            summary = manager.get_account_summary(current_user.id)
            
            # Publish portfolio value update
            await SyncEventPublisher.publish_account_update(
                user_id=current_user.id,
                account_id=0,  # Summary account
                data={
                    "total_value": float(summary.total_value) if summary.total_value else 0,
                    "total_cash": float(summary.total_cash) if summary.total_cash else 0,
                    "total_investments": float(summary.total_investments) if summary.total_investments else 0,
                    "account_count": summary.account_count
                }
            )
            
            # Publish sync completion
            await SyncEventPublisher.publish_sync_status_update(
                user_id=current_user.id,
                status="completed",
                message="Portfolio synchronization completed successfully"
            )
            
        finally:
            db.close()
        
        return {
            "message": "Portfolio sync triggered successfully",
            "user_id": current_user.id,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error triggering portfolio sync: {e}")
        
        # Publish sync error
        await SyncEventPublisher.publish_sync_status_update(
            user_id=current_user.id,
            status="error",
            message=f"Portfolio synchronization failed: {str(e)}"
        )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to trigger portfolio sync"
        )