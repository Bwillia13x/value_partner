import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import logging
from sqlalchemy.orm import Session
import yfinance as yf
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import mean_squared_error, r2_score
import joblib
import os

from .database import Account, Holding

logger = logging.getLogger(__name__)

class ModelType(Enum):
    RETURN_PREDICTION = "return_prediction"
    VOLATILITY_PREDICTION = "volatility_prediction"
    SECTOR_ROTATION = "sector_rotation"
    RISK_FACTOR = "risk_factor"
    PORTFOLIO_OPTIMIZATION = "portfolio_optimization"
    MARKET_REGIME = "market_regime"

class MLModelStatus(Enum):
    TRAINING = "training"
    READY = "ready"
    ERROR = "error"
    OUTDATED = "outdated"

@dataclass
class ModelPrediction:
    """ML model prediction result"""
    symbol: str
    prediction_type: str
    value: float
    confidence: float
    timestamp: datetime
    model_version: str
    features_used: List[str]

@dataclass
class ModelPerformance:
    """Model performance metrics"""
    model_name: str
    model_type: ModelType
    accuracy_score: float
    mse: float
    r2_score: float
    cross_val_score: float
    training_date: datetime
    validation_period: str

class FeatureEngineering:
    """Feature engineering for ML models"""
    
    @staticmethod
    def create_technical_features(price_data: pd.DataFrame) -> pd.DataFrame:
        """Create technical analysis features"""
        
        features = pd.DataFrame(index=price_data.index)
        
        # Price-based features
        features['close'] = price_data['Close']
        features['high'] = price_data['High']
        features['low'] = price_data['Low']
        features['volume'] = price_data['Volume']
        
        # Returns
        features['return_1d'] = price_data['Close'].pct_change()
        features['return_5d'] = price_data['Close'].pct_change(5)
        features['return_10d'] = price_data['Close'].pct_change(10)
        features['return_20d'] = price_data['Close'].pct_change(20)
        
        # Moving averages
        features['sma_5'] = price_data['Close'].rolling(5).mean()
        features['sma_10'] = price_data['Close'].rolling(10).mean()
        features['sma_20'] = price_data['Close'].rolling(20).mean()
        features['sma_50'] = price_data['Close'].rolling(50).mean()
        
        # Moving average ratios
        features['sma_ratio_5_20'] = features['sma_5'] / features['sma_20']
        features['sma_ratio_10_50'] = features['sma_10'] / features['sma_50']
        
        # Exponential moving averages
        features['ema_12'] = price_data['Close'].ewm(span=12).mean()
        features['ema_26'] = price_data['Close'].ewm(span=26).mean()
        
        # MACD
        features['macd'] = features['ema_12'] - features['ema_26']
        features['macd_signal'] = features['macd'].ewm(span=9).mean()
        features['macd_histogram'] = features['macd'] - features['macd_signal']
        
        # RSI
        delta = price_data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        features['rsi'] = 100 - (100 / (1 + rs))
        
        # Bollinger Bands
        bb_middle = price_data['Close'].rolling(20).mean()
        bb_std = price_data['Close'].rolling(20).std()
        features['bb_upper'] = bb_middle + (bb_std * 2)
        features['bb_lower'] = bb_middle - (bb_std * 2)
        features['bb_width'] = (features['bb_upper'] - features['bb_lower']) / bb_middle
        features['bb_position'] = (price_data['Close'] - features['bb_lower']) / (features['bb_upper'] - features['bb_lower'])
        
        # Volatility features
        features['volatility_5d'] = features['return_1d'].rolling(5).std()
        features['volatility_10d'] = features['return_1d'].rolling(10).std()
        features['volatility_20d'] = features['return_1d'].rolling(20).std()
        
        # Volume features
        features['volume_sma_20'] = price_data['Volume'].rolling(20).mean()
        features['volume_ratio'] = price_data['Volume'] / features['volume_sma_20']
        
        # Price position features
        features['high_52w'] = price_data['High'].rolling(252).max()
        features['low_52w'] = price_data['Low'].rolling(252).min()
        features['price_position_52w'] = (price_data['Close'] - features['low_52w']) / (features['high_52w'] - features['low_52w'])
        
        # Momentum features
        features['momentum_5d'] = price_data['Close'] / price_data['Close'].shift(5) - 1
        features['momentum_10d'] = price_data['Close'] / price_data['Close'].shift(10) - 1
        features['momentum_20d'] = price_data['Close'] / price_data['Close'].shift(20) - 1
        
        return features.dropna()
        
    @staticmethod
    def create_market_features(symbols: List[str], period_days: int = 252) -> pd.DataFrame:
        """Create market-wide features"""
        
        try:
            # Get market data (SPY, VIX, treasury rates)
            market_symbols = ['SPY', '^VIX', '^TNX', '^DJI', '^IXIC']
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=period_days + 100)
            
            market_data = yf.download(market_symbols, start=start_date, end=end_date, progress=False)
            
            if market_data.empty:
                return pd.DataFrame()
                
            features = pd.DataFrame()
            
            # Market return features
            spy_close = market_data['Adj Close']['SPY'] if 'SPY' in market_data['Adj Close'].columns else pd.Series()
            if not spy_close.empty:
                features['market_return_1d'] = spy_close.pct_change()
                features['market_return_5d'] = spy_close.pct_change(5)
                features['market_volatility_20d'] = features['market_return_1d'].rolling(20).std()
                
            # VIX features
            vix_close = market_data['Adj Close']['^VIX'] if '^VIX' in market_data['Adj Close'].columns else pd.Series()
            if not vix_close.empty:
                features['vix_level'] = vix_close
                features['vix_change'] = vix_close.pct_change()
                features['vix_sma_20'] = vix_close.rolling(20).mean()
                
            # Interest rate features
            tnx_close = market_data['Adj Close']['^TNX'] if '^TNX' in market_data['Adj Close'].columns else pd.Series()
            if not tnx_close.empty:
                features['treasury_10y'] = tnx_close
                features['treasury_change'] = tnx_close.diff()
                
            return features.dropna()
            
        except Exception as e:
            logger.error(f"Failed to create market features: {e}")
            return pd.DataFrame()

class MLModelManager:
    """Machine learning model manager"""
    
    def __init__(self, db: Session):
        self.db = db
        self.models: Dict[str, Any] = {}
        self.scalers: Dict[str, StandardScaler] = {}
        self.model_status: Dict[str, MLModelStatus] = {}
        self.model_dir = "models/ml_models"
        
        # Create models directory if it doesn't exist
        os.makedirs(self.model_dir, exist_ok=True)
        
    def train_return_prediction_model(self, symbols: List[str], lookback_days: int = 500) -> ModelPerformance:
        """Train a model to predict stock returns"""
        
        logger.info(f"Training return prediction model for {len(symbols)} symbols")
        
        try:
            # Prepare training data
            X, y = self._prepare_return_prediction_data(symbols, lookback_days)
            
            if X.empty or len(y) == 0:
                raise ValueError("Insufficient data for training")
                
            # Split data
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, shuffle=False
            )
            
            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Train model
            model = RandomForestRegressor(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                n_jobs=-1
            )
            
            model.fit(X_train_scaled, y_train)
            
            # Evaluate model
            y_pred = model.predict(X_test_scaled)
            mse = mean_squared_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)
            
            # Cross-validation
            cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=5, scoring='r2')
            cv_score = cv_scores.mean()
            
            # Save model and scaler
            model_name = "return_prediction"
            self.models[model_name] = model
            self.scalers[model_name] = scaler
            self.model_status[model_name] = MLModelStatus.READY
            
            # Save to disk
            joblib.dump(model, os.path.join(self.model_dir, f"{model_name}_model.pkl"))
            joblib.dump(scaler, os.path.join(self.model_dir, f"{model_name}_scaler.pkl"))
            
            performance = ModelPerformance(
                model_name=model_name,
                model_type=ModelType.RETURN_PREDICTION,
                accuracy_score=r2,
                mse=mse,
                r2_score=r2,
                cross_val_score=cv_score,
                training_date=datetime.now(),
                validation_period=f"{len(X_test)} days"
            )
            
            logger.info(f"Model trained successfully. R² score: {r2:.4f}")
            return performance
            
        except Exception as e:
            logger.error(f"Failed to train return prediction model: {e}")
            self.model_status["return_prediction"] = MLModelStatus.ERROR
            raise
            
    def predict_returns(self, symbols: List[str], horizon_days: int = 5) -> List[ModelPrediction]:
        """Predict future returns for symbols"""
        
        model_name = "return_prediction"
        
        if model_name not in self.models or self.model_status.get(model_name) != MLModelStatus.READY:
            raise ValueError("Return prediction model not available")
            
        try:
            predictions = []
            
            for symbol in symbols:
                # Get recent features
                features = self._get_recent_features(symbol)
                
                if features.empty:
                    continue
                    
                # Scale features
                scaler = self.scalers[model_name]
                features_scaled = scaler.transform(features.values.reshape(1, -1))
                
                # Make prediction
                model = self.models[model_name]
                predicted_return = model.predict(features_scaled)[0]
                
                # Calculate confidence (simplified)
                confidence = min(0.9, max(0.1, 0.7 - abs(predicted_return) * 5))
                
                prediction = ModelPrediction(
                    symbol=symbol,
                    prediction_type="return_prediction",
                    value=predicted_return,
                    confidence=confidence,
                    timestamp=datetime.now(),
                    model_version="1.0",
                    features_used=list(features.index)
                )
                
                predictions.append(prediction)
                
            return predictions
            
        except Exception as e:
            logger.error(f"Failed to predict returns: {e}")
            return []
            
    def train_portfolio_optimization_model(self, user_id: int) -> ModelPerformance:
        """Train a model for portfolio optimization recommendations"""
        
        logger.info(f"Training portfolio optimization model for user {user_id}")
        
        try:
            # Get user's historical portfolio data
            portfolio_data = self._get_user_portfolio_history(user_id)
            
            if not portfolio_data:
                raise ValueError("Insufficient portfolio data")
                
            # Prepare features and targets
            X, y = self._prepare_optimization_data(portfolio_data)
            
            if X.empty or len(y) == 0:
                raise ValueError("Insufficient data for optimization model")
                
            # Train model
            model = GradientBoostingRegressor(
                n_estimators=100,
                learning_rate=0.1,
                max_depth=6,
                random_state=42
            )
            
            # Use time series split for validation
            split_point = int(len(X) * 0.8)
            X_train, X_test = X.iloc[:split_point], X.iloc[split_point:]
            y_train, y_test = y[:split_point], y[split_point:]
            
            # Scale and train
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            model.fit(X_train_scaled, y_train)
            
            # Evaluate
            y_pred = model.predict(X_test_scaled)
            mse = mean_squared_error(y_test, y_pred)
            r2 = r2_score(y_test, y_pred)
            
            # Save model
            model_name = f"portfolio_optimization_{user_id}"
            self.models[model_name] = model
            self.scalers[model_name] = scaler
            self.model_status[model_name] = MLModelStatus.READY
            
            performance = ModelPerformance(
                model_name=model_name,
                model_type=ModelType.PORTFOLIO_OPTIMIZATION,
                accuracy_score=r2,
                mse=mse,
                r2_score=r2,
                cross_val_score=0.0,  # Not applicable for time series
                training_date=datetime.now(),
                validation_period=f"{len(X_test)} periods"
            )
            
            logger.info(f"Portfolio optimization model trained. R² score: {r2:.4f}")
            return performance
            
        except Exception as e:
            logger.error(f"Failed to train portfolio optimization model: {e}")
            raise
            
    def get_portfolio_recommendations(self, user_id: int) -> Dict[str, Any]:
        """Get ML-driven portfolio recommendations"""
        
        model_name = f"portfolio_optimization_{user_id}"
        
        if model_name not in self.models:
            # Try to load from disk or retrain
            try:
                self.load_model(model_name)
            except:
                logger.info("Training new portfolio optimization model")
                self.train_portfolio_optimization_model(user_id)
                
        try:
            # Get current portfolio
            current_portfolio = self._get_current_portfolio_weights(user_id)
            
            if not current_portfolio:
                return {"error": "No portfolio data available"}
                
            # Get market features
            market_features = FeatureEngineering.create_market_features(['SPY'])
            
            if market_features.empty:
                return {"error": "Unable to get market data"}
                
            recent_features = market_features.iloc[-1:]
            
            # Make recommendations
            model = self.models[model_name]
            scaler = self.scalers[model_name]
            
            # This is simplified - in practice you'd have more sophisticated feature engineering
            features_scaled = scaler.transform(recent_features.values)
            predicted_performance = model.predict(features_scaled)[0]
            
            recommendations = {
                "user_id": user_id,
                "predicted_performance": predicted_performance,
                "confidence": 0.7,  # Simplified confidence
                "recommendations": [
                    {
                        "type": "rebalance",
                        "description": "Consider rebalancing based on current market conditions",
                        "urgency": "medium"
                    },
                    {
                        "type": "diversification",
                        "description": "Evaluate sector diversification opportunities",
                        "urgency": "low"
                    }
                ],
                "timestamp": datetime.now().isoformat()
            }
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Failed to generate portfolio recommendations: {e}")
            return {"error": str(e)}
            
    def load_model(self, model_name: str):
        """Load model from disk"""
        try:
            model_path = os.path.join(self.model_dir, f"{model_name}_model.pkl")
            scaler_path = os.path.join(self.model_dir, f"{model_name}_scaler.pkl")
            
            if os.path.exists(model_path) and os.path.exists(scaler_path):
                self.models[model_name] = joblib.load(model_path)
                self.scalers[model_name] = joblib.load(scaler_path)
                self.model_status[model_name] = MLModelStatus.READY
                logger.info(f"Loaded model {model_name} from disk")
            else:
                raise FileNotFoundError(f"Model files not found for {model_name}")
                
        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {e}")
            self.model_status[model_name] = MLModelStatus.ERROR
            raise
            
    def _prepare_return_prediction_data(self, symbols: List[str], lookback_days: int) -> Tuple[pd.DataFrame, np.ndarray]:
        """Prepare data for return prediction model"""
        
        all_features = []
        all_targets = []
        
        for symbol in symbols:
            try:
                # Get price data
                end_date = datetime.now()
                start_date = end_date - timedelta(days=lookback_days + 100)
                
                ticker = yf.Ticker(symbol)
                price_data = ticker.history(start=start_date, end=end_date)
                
                if price_data.empty or len(price_data) < 50:
                    continue
                    
                # Create features
                features = FeatureEngineering.create_technical_features(price_data)
                
                # Create target (next day return)
                target = price_data['Close'].pct_change().shift(-1)  # Next day return
                
                # Align features and target
                aligned_data = pd.concat([features, target.rename('target')], axis=1).dropna()
                
                if len(aligned_data) < 30:
                    continue
                    
                all_features.append(aligned_data.drop('target', axis=1))
                all_targets.extend(aligned_data['target'].values)
                
            except Exception as e:
                logger.warning(f"Failed to prepare data for {symbol}: {e}")
                continue
                
        if all_features:
            X = pd.concat(all_features, ignore_index=True)
            y = np.array(all_targets)
            return X, y
        else:
            return pd.DataFrame(), np.array([])
            
    def _get_recent_features(self, symbol: str) -> pd.Series:
        """Get recent features for a symbol"""
        
        try:
            # Get recent price data
            ticker = yf.Ticker(symbol)
            price_data = ticker.history(period="3mo")
            
            if price_data.empty:
                return pd.Series()
                
            # Create features
            features = FeatureEngineering.create_technical_features(price_data)
            
            if features.empty:
                return pd.Series()
                
            # Return most recent features
            return features.iloc[-1]
            
        except Exception as e:
            logger.error(f"Failed to get recent features for {symbol}: {e}")
            return pd.Series()
            
    def _get_user_portfolio_history(self, user_id: int) -> Optional[Dict]:
        """Get user's portfolio history (simplified)"""
        
        # This is a placeholder - in practice you'd get actual portfolio history
        # from database or historical snapshots
        return {
            "dates": pd.date_range(start="2023-01-01", end="2024-01-01", freq="D"),
            "returns": np.random.normal(0.0005, 0.02, 365),  # Simulated returns
            "weights": {"AAPL": 0.3, "MSFT": 0.3, "GOOGL": 0.2, "SPY": 0.2}
        }
        
    def _prepare_optimization_data(self, portfolio_data: Dict) -> Tuple[pd.DataFrame, np.ndarray]:
        """Prepare data for portfolio optimization model"""
        
        # This is simplified - in practice you'd use more sophisticated features
        dates = portfolio_data["dates"]
        returns = portfolio_data["returns"]
        
        # Create simple features
        features = pd.DataFrame({
            "return_1d": returns,
            "return_5d_ma": pd.Series(returns).rolling(5).mean(),
            "volatility_10d": pd.Series(returns).rolling(10).std()
        })
        
        # Target is next period return
        target = pd.Series(returns).shift(-1)
        
        # Align and clean
        aligned_data = pd.concat([features, target.rename('target')], axis=1).dropna()
        
        X = aligned_data.drop('target', axis=1)
        y = aligned_data['target'].values
        
        return X, y
        
    def _get_current_portfolio_weights(self, user_id: int) -> Optional[Dict[str, float]]:
        """Get current portfolio weights"""
        
        try:
            # Get user's accounts
            accounts = self.db.query(Account).filter(
                Account.user_id == user_id,
                Account.account_type.in_(['investment', 'retirement'])
            ).all()
            
            total_value = 0.0
            positions = {}
            
            for account in accounts:
                holdings = self.db.query(Holding).filter(Holding.account_id == account.id).all()
                
                for holding in holdings:
                    if holding.symbol and holding.market_value:
                        if holding.symbol not in positions:
                            positions[holding.symbol] = 0.0
                        positions[holding.symbol] += holding.market_value
                        total_value += holding.market_value
                        
            if total_value > 0:
                return {symbol: value / total_value for symbol, value in positions.items()}
            else:
                return None
                
        except Exception as e:
            logger.error(f"Failed to get portfolio weights for user {user_id}: {e}")
            return None

# Global ML model manager
ml_model_manager = None

def get_ml_manager(db: Session) -> MLModelManager:
    """Get or create ML model manager"""
    global ml_model_manager
    if ml_model_manager is None:
        ml_model_manager = MLModelManager(db)
    return ml_model_manager