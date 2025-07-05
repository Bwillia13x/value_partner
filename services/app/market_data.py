import yfinance as yf
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum
import logging
from sqlalchemy.orm import Session
import threading
import time
from collections import defaultdict

from .database import Holding

logger = logging.getLogger(__name__)

class DataFeedType(Enum):
    REAL_TIME = "real_time"
    DELAYED = "delayed"
    HISTORICAL = "historical"

class MarketDataType(Enum):
    QUOTE = "quote"
    TRADE = "trade"
    LEVEL2 = "level2"
    NEWS = "news"
    FUNDAMENTALS = "fundamentals"

@dataclass
class Quote:
    """Real-time quote data"""
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

@dataclass
class Trade:
    """Trade data"""
    symbol: str
    price: float
    size: int
    timestamp: datetime
    exchange: str
    conditions: List[str] = None

@dataclass
class MarketAlert:
    """Market alert configuration"""
    symbol: str
    alert_type: str  # price, volume, volatility, news
    condition: str   # above, below, equal
    threshold: float
    user_id: int
    enabled: bool = True
    created_at: datetime = None

class MarketDataManager:
    """Real-time market data manager"""
    
    def __init__(self):
        self.subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self.quotes: Dict[str, Quote] = {}
        self.alerts: List[MarketAlert] = []
        self.is_running = False
        self.update_thread = None
        self.websocket_connections = {}
        
    def start(self):
        """Start the market data service"""
        if self.is_running:
            return
            
        self.is_running = True
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()
        logger.info("Market data manager started")
        
    def stop(self):
        """Stop the market data service"""
        self.is_running = False
        if self.update_thread:
            self.update_thread.join()
        logger.info("Market data manager stopped")
        
    def subscribe(self, symbol: str, callback: Callable[[Quote], None]):
        """Subscribe to real-time quotes for a symbol"""
        self.subscribers[symbol].append(callback)
        logger.info(f"Subscribed to {symbol}")
        
    def unsubscribe(self, symbol: str, callback: Callable[[Quote], None]):
        """Unsubscribe from symbol updates"""
        if symbol in self.subscribers and callback in self.subscribers[symbol]:
            self.subscribers[symbol].remove(callback)
            
    def get_quote(self, symbol: str) -> Optional[Quote]:
        """Get current quote for symbol"""
        return self.quotes.get(symbol)
        
    def get_quotes(self, symbols: List[str]) -> Dict[str, Quote]:
        """Get current quotes for multiple symbols"""
        return {symbol: self.quotes[symbol] for symbol in symbols if symbol in self.quotes}
        
    def add_alert(self, alert: MarketAlert):
        """Add a market alert"""
        alert.created_at = datetime.now()
        self.alerts.append(alert)
        logger.info(f"Added alert for {alert.symbol}")
        
    def remove_alert(self, symbol: str, user_id: int):
        """Remove alerts for symbol and user"""
        self.alerts = [a for a in self.alerts if not (a.symbol == symbol and a.user_id == user_id)]
        
    def get_historical_data(self, symbol: str, period: str = "1y") -> pd.DataFrame:
        """Get historical price data"""
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period)
            return data
        except Exception as e:
            logger.error(f"Failed to get historical data for {symbol}: {e}")
            return pd.DataFrame()
            
    def get_fundamentals(self, symbol: str) -> Dict[str, Any]:
        """Get fundamental data for symbol"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # Extract key fundamental metrics
            fundamentals = {
                'market_cap': info.get('marketCap'),
                'pe_ratio': info.get('trailingPE'),
                'forward_pe': info.get('forwardPE'),
                'pb_ratio': info.get('priceToBook'),
                'dividend_yield': info.get('dividendYield'),
                'beta': info.get('beta'),
                'eps': info.get('trailingEps'),
                'revenue': info.get('totalRevenue'),
                'revenue_growth': info.get('revenueGrowth'),
                'profit_margin': info.get('profitMargins'),
                'roe': info.get('returnOnEquity'),
                'debt_to_equity': info.get('debtToEquity'),
                'current_ratio': info.get('currentRatio'),
                'book_value': info.get('bookValue'),
                'enterprise_value': info.get('enterpriseValue'),
                'ebitda': info.get('ebitda'),
                'sector': info.get('sector'),
                'industry': info.get('industry'),
                'country': info.get('country'),
                'website': info.get('website'),
                'business_summary': info.get('longBusinessSummary')
            }
            
            return {k: v for k, v in fundamentals.items() if v is not None}
            
        except Exception as e:
            logger.error(f"Failed to get fundamentals for {symbol}: {e}")
            return {}
            
    def get_options_data(self, symbol: str) -> Dict[str, Any]:
        """Get options data for symbol"""
        try:
            ticker = yf.Ticker(symbol)
            
            # Get option dates
            option_dates = ticker.options
            if not option_dates:
                return {}
                
            # Get options chain for first expiration
            options_chain = ticker.option_chain(option_dates[0])
            
            return {
                'expiration_dates': list(option_dates),
                'calls': options_chain.calls.to_dict('records'),
                'puts': options_chain.puts.to_dict('records')
            }
            
        except Exception as e:
            logger.error(f"Failed to get options data for {symbol}: {e}")
            return {}
            
    def calculate_technical_indicators(self, symbol: str, period: str = "1y") -> Dict[str, Any]:
        """Calculate technical indicators"""
        try:
            data = self.get_historical_data(symbol, period)
            if data.empty:
                return {}
                
            close = data['Close']
            high = data['High']
            low = data['Low']
            volume = data['Volume']
            
            # Simple Moving Averages
            sma_20 = close.rolling(window=20).mean().iloc[-1]
            sma_50 = close.rolling(window=50).mean().iloc[-1]
            sma_200 = close.rolling(window=200).mean().iloc[-1]
            
            # Exponential Moving Averages
            ema_12 = close.ewm(span=12).mean().iloc[-1]
            ema_26 = close.ewm(span=26).mean().iloc[-1]
            
            # MACD
            macd = ema_12 - ema_26
            macd_signal = close.ewm(span=9).mean().iloc[-1]
            macd_histogram = macd - macd_signal
            
            # RSI
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs)).iloc[-1]
            
            # Bollinger Bands
            bb_middle = close.rolling(window=20).mean()
            bb_std = close.rolling(window=20).std()
            bb_upper = (bb_middle + (bb_std * 2)).iloc[-1]
            bb_lower = (bb_middle - (bb_std * 2)).iloc[-1]
            
            # Volume indicators
            avg_volume = volume.rolling(window=20).mean().iloc[-1]
            volume_ratio = volume.iloc[-1] / avg_volume if avg_volume > 0 else 0
            
            # Price position relative to 52-week range
            year_high = high.rolling(window=252).max().iloc[-1]
            year_low = low.rolling(window=252).min().iloc[-1]
            current_price = close.iloc[-1]
            
            if year_high > year_low:
                price_position = (current_price - year_low) / (year_high - year_low)
            else:
                price_position = 0.5
                
            return {
                'sma_20': sma_20,
                'sma_50': sma_50,
                'sma_200': sma_200,
                'ema_12': ema_12,
                'ema_26': ema_26,
                'macd': macd,
                'macd_signal': macd_signal,
                'macd_histogram': macd_histogram,
                'rsi': rsi,
                'bollinger_upper': bb_upper,
                'bollinger_lower': bb_lower,
                'bollinger_middle': bb_middle.iloc[-1],
                'avg_volume': avg_volume,
                'volume_ratio': volume_ratio,
                'year_high': year_high,
                'year_low': year_low,
                'price_position': price_position,
                'current_price': current_price
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate technical indicators for {symbol}: {e}")
            return {}
            
    def _update_loop(self):
        """Main update loop for market data"""
        while self.is_running:
            try:
                # Update quotes for subscribed symbols
                symbols_to_update = list(self.subscribers.keys())
                
                if symbols_to_update:
                    self._update_quotes(symbols_to_update)
                    self._check_alerts()
                    
                time.sleep(1)  # Update every second
                
            except Exception as e:
                logger.error(f"Error in market data update loop: {e}")
                time.sleep(5)  # Wait longer on error
                
    def _update_quotes(self, symbols: List[str]):
        """Update quotes for symbols"""
        try:
            # For demo purposes, use yfinance for real-time data
            # In production, you'd use a proper real-time data feed
            tickers = yf.Tickers(' '.join(symbols))
            
            for symbol in symbols:
                try:
                    ticker = tickers.tickers[symbol]
                    info = ticker.info
                    hist = ticker.history(period="1d", interval="1m")
                    
                    if not hist.empty:
                        current_price = hist['Close'].iloc[-1]
                        volume = hist['Volume'].iloc[-1]
                        open_price = hist['Open'].iloc[0]
                        high = hist['High'].max()
                        low = hist['Low'].min()
                        
                        previous_close = info.get('previousClose', current_price)
                        change = current_price - previous_close
                        change_percent = (change / previous_close * 100) if previous_close > 0 else 0
                        
                        quote = Quote(
                            symbol=symbol,
                            bid=info.get('bid', current_price),
                            ask=info.get('ask', current_price),
                            bid_size=info.get('bidSize', 0),
                            ask_size=info.get('askSize', 0),
                            last_price=current_price,
                            last_size=0,
                            volume=int(volume),
                            timestamp=datetime.now(),
                            change=change,
                            change_percent=change_percent,
                            high=high,
                            low=low,
                            open=open_price,
                            previous_close=previous_close
                        )
                        
                        # Update quote and notify subscribers
                        old_quote = self.quotes.get(symbol)
                        self.quotes[symbol] = quote
                        
                        # Notify subscribers if price changed
                        if not old_quote or old_quote.last_price != quote.last_price:
                            for callback in self.subscribers[symbol]:
                                try:
                                    callback(quote)
                                except Exception as e:
                                    logger.error(f"Error in quote callback for {symbol}: {e}")
                                    
                except Exception as e:
                    logger.error(f"Failed to update quote for {symbol}: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to update quotes: {e}")
            
    def _check_alerts(self):
        """Check and trigger market alerts"""
        for alert in self.alerts:
            if not alert.enabled:
                continue
                
            quote = self.quotes.get(alert.symbol)
            if not quote:
                continue
                
            triggered = False
            current_value = None
            
            if alert.alert_type == "price":
                current_value = quote.last_price
            elif alert.alert_type == "volume":
                current_value = quote.volume
            elif alert.alert_type == "volatility":
                current_value = abs(quote.change_percent)
                
            if current_value is not None:
                if alert.condition == "above" and current_value > alert.threshold:
                    triggered = True
                elif alert.condition == "below" and current_value < alert.threshold:
                    triggered = True
                elif alert.condition == "equal" and abs(current_value - alert.threshold) < 0.01:
                    triggered = True
                    
            if triggered:
                self._trigger_alert(alert, quote, current_value)
                
    def _trigger_alert(self, alert: MarketAlert, quote: Quote, current_value: float):
        """Trigger a market alert"""
        logger.info(f"Alert triggered: {alert.symbol} {alert.alert_type} {alert.condition} {alert.threshold}")
        
        # In a real implementation, you'd send notifications here
        # For now, just log the alert
        
        # Disable alert to prevent spam (could be configurable)
        alert.enabled = False

# Global market data manager instance
market_data_manager = MarketDataManager()

def start_market_data():
    """Start the global market data manager"""
    market_data_manager.start()
    
def stop_market_data():
    """Stop the global market data manager"""
    market_data_manager.stop()

class PortfolioMonitor:
    """Monitor portfolio holdings for real-time updates"""
    
    def __init__(self, db: Session):
        self.db = db
        self.monitored_users: Dict[int, List[str]] = {}
        
    def start_monitoring_user(self, user_id: int):
        """Start monitoring a user's portfolio"""
        # Get user's holdings
        holdings = self.db.query(Holding).join(Holding.account).filter(
            Holding.account.has(user_id=user_id)
        ).all()
        
        symbols = list(set(holding.symbol for holding in holdings if holding.symbol))
        
        if symbols:
            self.monitored_users[user_id] = symbols
            
            # Subscribe to market data for each symbol
            for symbol in symbols:
                market_data_manager.subscribe(symbol, 
                    lambda quote, uid=user_id: self._on_quote_update(uid, quote))
                    
            logger.info(f"Started monitoring {len(symbols)} symbols for user {user_id}")
            
    def stop_monitoring_user(self, user_id: int):
        """Stop monitoring a user's portfolio"""
        if user_id in self.monitored_users:
            symbols = self.monitored_users[user_id]
            
            # Unsubscribe from market data
            for symbol in symbols:
                market_data_manager.unsubscribe(symbol, 
                    lambda quote, uid=user_id: self._on_quote_update(uid, quote))
                    
            del self.monitored_users[user_id]
            logger.info(f"Stopped monitoring user {user_id}")
            
    def _on_quote_update(self, user_id: int, quote: Quote):
        """Handle quote update for user"""
        # Update portfolio values in real-time
        # This could trigger rebalancing alerts, performance updates, etc.
        logger.debug(f"Quote update for user {user_id}: {quote.symbol} @ {quote.last_price}")
        
        # In a real implementation, you might:
        # 1. Update cached portfolio values
        # 2. Check for rebalancing needs
        # 3. Send real-time updates to frontend
        # 4. Trigger alerts based on portfolio changes