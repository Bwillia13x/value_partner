from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List, Optional, Dict
from pydantic import BaseModel
from datetime import datetime
import json
import asyncio
import random

from .database import get_db
from .market_data import (
    market_data_manager, 
    MarketAlert,
    Quote,
    PortfolioMonitor
)

router = APIRouter(prefix="/market-data", tags=["market-data"])


class QuoteResponse(BaseModel):
    """Quote response model"""
    symbol: str
    bid: float
    ask: float
    bid_size: int
    ask_size: int
    last_price: float
    last_size: int
    volume: int
    timestamp: datetime
    change: float
    change_percent: float
    high: float
    low: float
    open: float
    previous_close: float


class AlertRequest(BaseModel):
    """Market alert request model"""
    symbol: str
    alert_type: str  # price, volume, volatility
    condition: str   # above, below, equal
    threshold: float
    enabled: bool = True


class TechnicalIndicatorsResponse(BaseModel):
    """Technical indicators response model"""
    symbol: str
    sma_20: Optional[float] = None
    sma_50: Optional[float] = None
    sma_200: Optional[float] = None
    ema_12: Optional[float] = None
    ema_26: Optional[float] = None
    macd: Optional[float] = None
    rsi: Optional[float] = None
    bollinger_upper: Optional[float] = None
    bollinger_lower: Optional[float] = None
    volume_ratio: Optional[float] = None
    year_high: Optional[float] = None
    year_low: Optional[float] = None
    price_position: Optional[float] = None
    current_price: Optional[float] = None


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.user_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: Optional[int] = None):
        await websocket.accept()
        self.active_connections.append(websocket)
        if user_id:
            if user_id not in self.user_connections:
                self.user_connections[user_id] = []
            self.user_connections[user_id].append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: Optional[int] = None):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if user_id and user_id in self.user_connections:
            if websocket in self.user_connections[user_id]:
                self.user_connections[user_id].remove(websocket)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def send_to_user(self, message: str, user_id: int):
        if user_id in self.user_connections:
            for connection in self.user_connections[user_id]:
                await connection.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()


@router.get("/quote/{symbol}", response_model=QuoteResponse)
async def get_quote(
    symbol: str,
    db: Session = Depends(get_db)
):
    """Get current quote for a symbol"""
    
    quote = market_data_manager.get_quote(symbol.upper())
    
    if not quote:
        # If not in cache, try to get from yfinance
        market_data_manager.subscribe(symbol.upper(), lambda q: None)
        await asyncio.sleep(2)  # Wait for data
        quote = market_data_manager.get_quote(symbol.upper())
        
    if not quote:
        # Fallback to mock data for demonstration
        from datetime import datetime
        
        # Common stock symbols with realistic price ranges
        mock_prices = {
            'AAPL': 150.0, 'MSFT': 300.0, 'GOOGL': 120.0, 'AMZN': 130.0,
            'TSLA': 200.0, 'META': 250.0, 'NVDA': 400.0, 'JPM': 140.0,
            'JNJ': 160.0, 'PG': 140.0, 'SPY': 430.0, 'QQQ': 350.0
        }
        
        base_price = mock_prices.get(symbol.upper(), 100.0)
        current_price = base_price + random.uniform(-5.0, 5.0)
        previous_close = base_price
        change = current_price - previous_close
        change_percent = (change / previous_close) * 100
        
        return QuoteResponse(
            symbol=symbol.upper(),
            bid=current_price - 0.02,
            ask=current_price + 0.02,
            bid_size=100,
            ask_size=100,
            last_price=current_price,
            last_size=100,
            volume=random.randint(1000000, 10000000),
            timestamp=datetime.now(),
            change=change,
            change_percent=change_percent,
            high=current_price + random.uniform(0, 3),
            low=current_price - random.uniform(0, 3),
            open=previous_close + random.uniform(-2, 2),
            previous_close=previous_close
        )
    
    return QuoteResponse(
        symbol=quote.symbol,
        bid=quote.bid,
        ask=quote.ask,
        bid_size=quote.bid_size,
        ask_size=quote.ask_size,
        last_price=quote.last_price,
        last_size=quote.last_size,
        volume=quote.volume,
        timestamp=quote.timestamp,
        change=quote.change,
        change_percent=quote.change_percent,
        high=quote.high,
        low=quote.low,
        open=quote.open,
        previous_close=quote.previous_close
    )


@router.get("/quotes", response_model=List[QuoteResponse])
async def get_quotes(
    symbols: str,  # Comma-separated symbols
    db: Session = Depends(get_db)
):
    """Get quotes for multiple symbols"""
    
    symbol_list = [s.strip().upper() for s in symbols.split(',')]
    quotes = market_data_manager.get_quotes(symbol_list)
    
    # Subscribe to any missing symbols
    for symbol in symbol_list:
        if symbol not in quotes:
            market_data_manager.subscribe(symbol, lambda q: None)
    
    if len(quotes) < len(symbol_list):
        await asyncio.sleep(2)  # Wait for data
        quotes = market_data_manager.get_quotes(symbol_list)
    
    return [
        QuoteResponse(
            symbol=quote.symbol,
            bid=quote.bid,
            ask=quote.ask,
            bid_size=quote.bid_size,
            ask_size=quote.ask_size,
            last_price=quote.last_price,
            last_size=quote.last_size,
            volume=quote.volume,
            timestamp=quote.timestamp,
            change=quote.change,
            change_percent=quote.change_percent,
            high=quote.high,
            low=quote.low,
            open=quote.open,
            previous_close=quote.previous_close
        )
        for quote in quotes.values()
    ]


@router.get("/historical/{symbol}")
async def get_historical_data(
    symbol: str,
    period: str = "1y",
    interval: str = "1d",
    db: Session = Depends(get_db)
):
    """Get historical price data"""
    
    try:
        data = market_data_manager.get_historical_data(symbol.upper(), period)
        
        if data.empty:
            raise HTTPException(status_code=404, detail=f"No historical data found for {symbol}")
        
        # Convert to JSON-serializable format
        result = {
            "symbol": symbol.upper(),
            "period": period,
            "data": [
                {
                    "date": date.strftime("%Y-%m-%d"),
                    "open": row['Open'],
                    "high": row['High'],
                    "low": row['Low'],
                    "close": row['Close'],
                    "volume": row['Volume']
                }
                for date, row in data.iterrows()
            ]
        }
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fundamentals/{symbol}")
async def get_fundamentals(
    symbol: str,
    db: Session = Depends(get_db)
):
    """Get fundamental data for a symbol"""
    
    try:
        fundamentals = market_data_manager.get_fundamentals(symbol.upper())
        
        if not fundamentals:
            raise HTTPException(status_code=404, detail=f"No fundamental data found for {symbol}")
        
        return {
            "symbol": symbol.upper(),
            "fundamentals": fundamentals
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/technical/{symbol}", response_model=TechnicalIndicatorsResponse)
async def get_technical_indicators(
    symbol: str,
    period: str = "1y",
    db: Session = Depends(get_db)
):
    """Get technical indicators for a symbol"""
    
    try:
        indicators = market_data_manager.calculate_technical_indicators(symbol.upper(), period)
        
        if not indicators:
            raise HTTPException(status_code=404, detail=f"No technical data found for {symbol}")
        
        return TechnicalIndicatorsResponse(
            symbol=symbol.upper(),
            **indicators
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/options/{symbol}")
async def get_options_data(
    symbol: str,
    db: Session = Depends(get_db)
):
    """Get options data for a symbol"""
    
    try:
        options_data = market_data_manager.get_options_data(symbol.upper())
        
        if not options_data:
            raise HTTPException(status_code=404, detail=f"No options data found for {symbol}")
        
        return {
            "symbol": symbol.upper(),
            "options": options_data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/alerts/{user_id}")
async def create_alert(
    user_id: int,
    alert: AlertRequest,
    db: Session = Depends(get_db)
):
    """Create a market alert"""
    
    try:
        market_alert = MarketAlert(
            symbol=alert.symbol.upper(),
            alert_type=alert.alert_type,
            condition=alert.condition,
            threshold=alert.threshold,
            user_id=user_id,
            enabled=alert.enabled
        )
        
        market_data_manager.add_alert(market_alert)
        
        # Subscribe to symbol if not already subscribed
        market_data_manager.subscribe(alert.symbol.upper(), lambda q: None)
        
        return {
            "message": f"Alert created for {alert.symbol}",
            "alert": {
                "symbol": market_alert.symbol,
                "alert_type": market_alert.alert_type,
                "condition": market_alert.condition,
                "threshold": market_alert.threshold,
                "enabled": market_alert.enabled
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/alerts/{user_id}/{symbol}")
async def remove_alerts(
    user_id: int,
    symbol: str,
    db: Session = Depends(get_db)
):
    """Remove all alerts for a symbol and user"""
    
    market_data_manager.remove_alert(symbol.upper(), user_id)
    
    return {"message": f"Alerts removed for {symbol}"}


@router.get("/alerts/{user_id}")
async def get_user_alerts(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Get all alerts for a user"""
    
    user_alerts = [alert for alert in market_data_manager.alerts if alert.user_id == user_id]
    
    return {
        "user_id": user_id,
        "alerts": [
            {
                "symbol": alert.symbol,
                "alert_type": alert.alert_type,
                "condition": alert.condition,
                "threshold": alert.threshold,
                "enabled": alert.enabled,
                "created_at": alert.created_at.isoformat() if alert.created_at else None
            }
            for alert in user_alerts
        ]
    }


@router.post("/monitor/start/{user_id}")
async def start_portfolio_monitoring(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Start monitoring a user's portfolio for real-time updates"""
    
    try:
        monitor = PortfolioMonitor(db)
        monitor.start_monitoring_user(user_id)
        
        return {"message": f"Started monitoring portfolio for user {user_id}"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/monitor/stop/{user_id}")
async def stop_portfolio_monitoring(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Stop monitoring a user's portfolio"""
    
    try:
        monitor = PortfolioMonitor(db)
        monitor.stop_monitoring_user(user_id)
        
        return {"message": f"Stopped monitoring portfolio for user {user_id}"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    """WebSocket endpoint for real-time market data"""
    await manager.connect(websocket, user_id)
    
    try:
        while True:
            # Keep connection alive and handle incoming messages
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("action") == "subscribe":
                symbol = message.get("symbol", "").upper()
                if symbol:
                    # Subscribe to symbol and send updates to this WebSocket
                    def quote_callback(quote: Quote):
                        asyncio.create_task(
                            manager.send_personal_message(
                                json.dumps({
                                    "type": "quote",
                                    "symbol": quote.symbol,
                                    "price": quote.last_price,
                                    "change": quote.change,
                                    "change_percent": quote.change_percent,
                                    "timestamp": quote.timestamp.isoformat()
                                }),
                                websocket
                            )
                        )
                    
                    market_data_manager.subscribe(symbol, quote_callback)
                    
            elif message.get("action") == "unsubscribe":
                symbol = message.get("symbol", "").upper()
                # Would need to track callbacks to unsubscribe properly
                pass
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)


@router.get("/market-status")
async def get_market_status():
    """Get current market status"""
    
    try:
        # This is a simplified market status check
        # In practice, you'd check multiple exchanges and market hours
        
        now = datetime.now()
        
        # Basic US market hours check (9:30 AM - 4:00 PM ET, Mon-Fri)
        # This is simplified and doesn't account for holidays
        is_weekend = now.weekday() >= 5
        hour = now.hour
        minute = now.minute
        
        # Convert to market time (simplified - doesn't handle timezones properly)
        market_open = hour >= 9 and (hour < 16 or (hour == 9 and minute >= 30))
        
        market_status = "closed"
        if not is_weekend and market_open:
            market_status = "open"
        elif not is_weekend and (hour < 9 or (hour == 9 and minute < 30)):
            market_status = "pre_market"
        elif not is_weekend and hour >= 16:
            market_status = "after_hours"
        
        return {
            "market_status": market_status,
            "is_weekend": is_weekend,
            "current_time": now.isoformat(),
            "next_open": "2024-01-02 09:30:00",  # Would calculate actual next open
            "next_close": "2024-01-02 16:00:00"  # Would calculate actual next close
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/screener")
async def stock_screener(
    min_market_cap: Optional[float] = None,
    max_pe_ratio: Optional[float] = None,
    min_dividend_yield: Optional[float] = None,
    sector: Optional[str] = None,
    limit: int = 50
):
    """Basic stock screener"""
    
    # This is a simplified screener
    # In practice, you'd query a comprehensive stock database
    
    try:
        # Sample symbols to screen (in practice, this would be much larger)
        symbols = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'META', 'NVDA', 'JPM', 'JNJ', 'PG']
        
        results = []
        
        for symbol in symbols[:limit]:
            try:
                fundamentals = market_data_manager.get_fundamentals(symbol)
                
                if not fundamentals:
                    continue
                    
                # Apply filters
                if min_market_cap and fundamentals.get('market_cap', 0) < min_market_cap:
                    continue
                    
                if max_pe_ratio and fundamentals.get('pe_ratio', float('inf')) > max_pe_ratio:
                    continue
                    
                if min_dividend_yield and fundamentals.get('dividend_yield', 0) < min_dividend_yield:
                    continue
                    
                if sector and fundamentals.get('sector', '').lower() != sector.lower():
                    continue
                    
                # Get current quote
                quote = market_data_manager.get_quote(symbol)
                current_price = quote.last_price if quote else fundamentals.get('current_price', 0)
                
                results.append({
                    'symbol': symbol,
                    'current_price': current_price,
                    'market_cap': fundamentals.get('market_cap'),
                    'pe_ratio': fundamentals.get('pe_ratio'),
                    'dividend_yield': fundamentals.get('dividend_yield'),
                    'sector': fundamentals.get('sector'),
                    'beta': fundamentals.get('beta')
                })
                
            except Exception:
                continue  # Skip symbols that fail
                
        return {
            'results': results,
            'total_found': len(results),
            'filters_applied': {
                'min_market_cap': min_market_cap,
                'max_pe_ratio': max_pe_ratio,
                'min_dividend_yield': min_dividend_yield,
                'sector': sector
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))