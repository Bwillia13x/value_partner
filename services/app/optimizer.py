import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from scipy.optimize import minimize
import yfinance as yf
from .database import User, Account, Holding, Strategy, StrategyHolding
from .analytics import PortfolioAnalytics
from dataclasses import dataclass


@dataclass
class OptimizationResult:
    """Results from portfolio optimization"""
    optimal_weights: Dict[str, float]
    expected_return: float
    expected_volatility: float
    sharpe_ratio: float
    current_weights: Dict[str, float]
    rebalance_trades: Dict[str, float]
    optimization_method: str


class PortfolioOptimizer:
    """Advanced portfolio optimization and recommendation engine"""
    
    def __init__(self, db: Session):
        self.db = db
        self.analytics = PortfolioAnalytics(db)
    
    def optimize_portfolio(self, 
                         user_id: int, 
                         method: str = "max_sharpe",
                         constraints: Optional[Dict] = None,
                         lookback_days: int = 252) -> Optional[OptimizationResult]:
        """
        Optimize portfolio allocation using various methods
        
        Args:
            user_id: User ID
            method: Optimization method ('max_sharpe', 'min_volatility', 'max_return')
            constraints: Optional constraints dict
            lookback_days: Historical data lookback period
        """
        
        # Get current portfolio
        current_portfolio = self._get_current_portfolio(user_id)
        if not current_portfolio:
            return None
        
        symbols = list(current_portfolio.keys())
        
        # Get historical data
        returns_data = self._get_historical_returns(symbols, lookback_days)
        if returns_data.empty:
            return None
        
        # Calculate expected returns and covariance matrix
        expected_returns = returns_data.mean() * 252  # Annualized
        cov_matrix = returns_data.cov() * 252  # Annualized
        
        # Perform optimization
        if method == "max_sharpe":
            optimal_weights = self._optimize_max_sharpe(expected_returns, cov_matrix, constraints)
        elif method == "min_volatility":
            optimal_weights = self._optimize_min_volatility(cov_matrix, constraints)
        elif method == "max_return":
            optimal_weights = self._optimize_max_return(expected_returns, constraints)
        else:
            return None
        
        # Calculate portfolio metrics
        portfolio_return = np.dot(optimal_weights, expected_returns)
        portfolio_volatility = np.sqrt(np.dot(optimal_weights.T, np.dot(cov_matrix, optimal_weights)))
        sharpe_ratio = portfolio_return / portfolio_volatility if portfolio_volatility > 0 else 0
        
        # Calculate rebalancing trades
        current_weights = self._normalize_weights(current_portfolio)
        optimal_weights_dict = {symbols[i]: optimal_weights[i] for i in range(len(symbols))}
        rebalance_trades = {symbol: optimal_weights_dict[symbol] - current_weights.get(symbol, 0) 
                           for symbol in symbols}
        
        return OptimizationResult(
            optimal_weights=optimal_weights_dict,
            expected_return=portfolio_return,
            expected_volatility=portfolio_volatility,
            sharpe_ratio=sharpe_ratio,
            current_weights=current_weights,
            rebalance_trades=rebalance_trades,
            optimization_method=method
        )
    
    def _get_current_portfolio(self, user_id: int) -> Dict[str, float]:
        """Get current portfolio holdings as market values"""
        
        accounts = self.db.query(Account).filter(
            Account.user_id == user_id,
            Account.account_type.in_(['investment', 'retirement'])
        ).all()
        
        portfolio = {}
        
        for account in accounts:
            holdings = self.db.query(Holding).filter(Holding.account_id == account.id).all()
            
            for holding in holdings:
                if holding.symbol and holding.market_value > 0:
                    portfolio[holding.symbol] = portfolio.get(holding.symbol, 0) + holding.market_value
        
        return portfolio
    
    def _get_historical_returns(self, symbols: List[str], lookback_days: int) -> pd.DataFrame:
        """Get historical returns for given symbols"""
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=lookback_days + 30)  # Buffer for trading days
        
        returns_data = pd.DataFrame()
        
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(start=start_date, end=end_date)
                
                if len(hist) > 0:
                    returns = hist['Close'].pct_change().dropna()
                    returns_data[symbol] = returns
                    
            except Exception as e:
                print(f"Error fetching data for {symbol}: {e}")
                continue
        
        return returns_data.dropna()
    
    def _normalize_weights(self, portfolio: Dict[str, float]) -> Dict[str, float]:
        """Normalize portfolio weights to sum to 1"""
        
        total_value = sum(portfolio.values())
        if total_value == 0:
            return {}
        
        return {symbol: value / total_value for symbol, value in portfolio.items()}
    
    def _optimize_max_sharpe(self, expected_returns: pd.Series, cov_matrix: pd.DataFrame, 
                            constraints: Optional[Dict] = None) -> np.ndarray:
        """Optimize for maximum Sharpe ratio"""
        
        n_assets = len(expected_returns)
        
        def neg_sharpe(weights):
            portfolio_return = np.dot(weights, expected_returns)
            portfolio_volatility = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            return -portfolio_return / portfolio_volatility if portfolio_volatility > 0 else 0
        
        # Constraints
        cons = [{'type': 'eq', 'fun': lambda x: np.sum(x) - 1}]  # Weights sum to 1
        
        # Bounds (no short selling by default)
        bounds = tuple((0, 1) for _ in range(n_assets))
        
        # Add custom constraints if provided
        if constraints:
            if 'max_weight' in constraints:
                bounds = tuple((0, constraints['max_weight']) for _ in range(n_assets))
            if 'min_weight' in constraints:
                bounds = tuple((constraints['min_weight'], bounds[i][1]) for i in range(n_assets))
        
        # Initial guess (equal weights)
        x0 = np.array([1/n_assets] * n_assets)
        
        # Optimize
        result = minimize(neg_sharpe, x0, method='SLSQP', bounds=bounds, constraints=cons)
        
        return result.x if result.success else x0
    
    def _optimize_min_volatility(self, cov_matrix: pd.DataFrame, 
                                constraints: Optional[Dict] = None) -> np.ndarray:
        """Optimize for minimum volatility"""
        
        n_assets = len(cov_matrix)
        
        def portfolio_volatility(weights):
            return np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        
        # Constraints
        cons = [{'type': 'eq', 'fun': lambda x: np.sum(x) - 1}]
        
        # Bounds
        bounds = tuple((0, 1) for _ in range(n_assets))
        
        if constraints:
            if 'max_weight' in constraints:
                bounds = tuple((0, constraints['max_weight']) for _ in range(n_assets))
            if 'min_weight' in constraints:
                bounds = tuple((constraints['min_weight'], bounds[i][1]) for i in range(n_assets))
        
        # Initial guess
        x0 = np.array([1/n_assets] * n_assets)
        
        # Optimize
        result = minimize(portfolio_volatility, x0, method='SLSQP', bounds=bounds, constraints=cons)
        
        return result.x if result.success else x0
    
    def _optimize_max_return(self, expected_returns: pd.Series, 
                           constraints: Optional[Dict] = None) -> np.ndarray:
        """Optimize for maximum expected return"""
        
        n_assets = len(expected_returns)
        
        def neg_return(weights):
            return -np.dot(weights, expected_returns)
        
        # Constraints
        cons = [{'type': 'eq', 'fun': lambda x: np.sum(x) - 1}]
        
        # Bounds
        bounds = tuple((0, 1) for _ in range(n_assets))
        
        if constraints:
            if 'max_weight' in constraints:
                bounds = tuple((0, constraints['max_weight']) for _ in range(n_assets))
            if 'min_weight' in constraints:
                bounds = tuple((constraints['min_weight'], bounds[i][1]) for i in range(n_assets))
        
        # Initial guess
        x0 = np.array([1/n_assets] * n_assets)
        
        # Optimize
        result = minimize(neg_return, x0, method='SLSQP', bounds=bounds, constraints=cons)
        
        return result.x if result.success else x0
    
    def generate_efficient_frontier(self, user_id: int, n_portfolios: int = 50) -> List[Dict]:
        """Generate efficient frontier data points"""
        
        current_portfolio = self._get_current_portfolio(user_id)
        if not current_portfolio:
            return []
        
        symbols = list(current_portfolio.keys())
        returns_data = self._get_historical_returns(symbols, 252)
        
        if returns_data.empty:
            return []
        
        expected_returns = returns_data.mean() * 252
        cov_matrix = returns_data.cov() * 252
        
        # Generate range of target returns
        min_return = expected_returns.min()
        max_return = expected_returns.max()
        target_returns = np.linspace(min_return, max_return, n_portfolios)
        
        efficient_portfolios = []
        
        for target_return in target_returns:
            try:
                # Optimize for minimum volatility given target return
                n_assets = len(expected_returns)
                
                def portfolio_volatility(weights):
                    return np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
                
                # Constraints
                cons = [
                    {'type': 'eq', 'fun': lambda x: np.sum(x) - 1},  # Weights sum to 1
                    {'type': 'eq', 'fun': lambda x: np.dot(x, expected_returns) - target_return}  # Target return
                ]
                
                bounds = tuple((0, 1) for _ in range(n_assets))
                x0 = np.array([1/n_assets] * n_assets)
                
                result = minimize(portfolio_volatility, x0, method='SLSQP', bounds=bounds, constraints=cons)
                
                if result.success:
                    portfolio_vol = portfolio_volatility(result.x)
                    efficient_portfolios.append({
                        'return': target_return,
                        'volatility': portfolio_vol,
                        'sharpe_ratio': target_return / portfolio_vol if portfolio_vol > 0 else 0,
                        'weights': {symbols[i]: result.x[i] for i in range(len(symbols))}
                    })
                    
            except Exception as e:
                print(f"Error calculating efficient frontier point: {e}")
                continue
        
        return efficient_portfolios
    
    def get_rebalancing_recommendations(self, user_id: int) -> List[Dict]:
        """Get specific rebalancing recommendations"""
        
        # Get user's strategies
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return []
        
        strategies = self.db.query(Strategy).filter(Strategy.user_id == user_id).all()
        
        recommendations = []
        
        for strategy in strategies:
            # Get target allocation
            target_holdings = self.db.query(StrategyHolding).filter(
                StrategyHolding.strategy_id == strategy.id
            ).all()
            
            if not target_holdings:
                continue
            
            target_weights = {h.symbol: h.target_weight for h in target_holdings}
            
            # Get current allocation
            current_portfolio = self._get_current_portfolio(user_id)
            current_weights = self._normalize_weights(current_portfolio)
            
            # Calculate drift
            total_value = sum(current_portfolio.values())
            
            for target_holding in target_holdings:
                symbol = target_holding.symbol
                target_weight = target_holding.target_weight
                current_weight = current_weights.get(symbol, 0)
                
                drift = abs(current_weight - target_weight)
                
                if drift > strategy.rebalance_threshold / 100:  # Convert percentage to decimal
                    target_value = total_value * target_weight
                    current_value = current_portfolio.get(symbol, 0)
                    trade_value = target_value - current_value
                    
                    recommendations.append({
                        'strategy_name': strategy.name,
                        'symbol': symbol,
                        'action': 'BUY' if trade_value > 0 else 'SELL',
                        'current_weight': current_weight,
                        'target_weight': target_weight,
                        'drift': drift,
                        'trade_value': abs(trade_value),
                        'priority': 'HIGH' if drift > 0.1 else 'MEDIUM'
                    })
        
        return sorted(recommendations, key=lambda x: x['drift'], reverse=True)