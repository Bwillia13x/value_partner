import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import logging
from sqlalchemy.orm import Session
import yfinance as yf

from .database import Account, Holding
from .analytics import PortfolioAnalytics

logger = logging.getLogger(__name__)

class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class RiskType(Enum):
    CONCENTRATION = "concentration"
    VOLATILITY = "volatility"
    CORRELATION = "correlation"
    LIQUIDITY = "liquidity"
    CREDIT = "credit"
    MARKET = "market"
    CURRENCY = "currency"
    INTEREST_RATE = "interest_rate"

@dataclass
class RiskAlert:
    """Risk alert data structure"""
    risk_type: RiskType
    level: RiskLevel
    message: str
    value: float
    threshold: float
    recommendation: str
    created_at: datetime
    user_id: int
    symbol: Optional[str] = None

@dataclass
class RiskMetrics:
    """Portfolio risk metrics"""
    var_95: float  # Value at Risk (95% confidence)
    var_99: float  # Value at Risk (99% confidence)
    expected_shortfall: float  # Conditional VaR
    max_drawdown: float
    volatility: float
    beta: float
    tracking_error: float
    information_ratio: float
    concentration_risk: float
    correlation_risk: float
    liquidity_score: float
    
@dataclass
class PositionRisk:
    """Individual position risk metrics"""
    symbol: str
    weight: float
    volatility: float
    beta: float
    var_contribution: float
    concentration_score: float
    liquidity_score: float
    correlation_avg: float

class RiskManagementEngine:
    """Advanced risk management and monitoring system"""
    
    def __init__(self, db: Session):
        self.db = db
        self.analytics = PortfolioAnalytics(db)
        
        # Risk thresholds (configurable per user/strategy)
        self.risk_thresholds = {
            'max_position_weight': 0.20,  # 20% max single position
            'max_sector_weight': 0.30,    # 30% max sector allocation
            'max_portfolio_var': 0.05,    # 5% max daily VaR
            'max_volatility': 0.25,       # 25% max annual volatility
            'min_liquidity_score': 0.6,   # Minimum liquidity score
            'max_correlation': 0.8,       # Maximum average correlation
            'max_beta': 2.0,              # Maximum portfolio beta
            'max_tracking_error': 0.10    # 10% max tracking error
        }
        
    def assess_portfolio_risk(self, user_id: int, period_days: int = 252) -> Tuple[RiskMetrics, List[RiskAlert]]:
        """Comprehensive portfolio risk assessment"""
        
        logger.info(f"Assessing portfolio risk for user {user_id}")
        
        # Get portfolio data
        portfolio_data = self._get_portfolio_data(user_id)
        if not portfolio_data:
            return None, []
            
        symbols = list(portfolio_data.keys())
        weights = np.array([portfolio_data[symbol]['weight'] for symbol in symbols])
        
        # Get price data and calculate returns
        returns_data = self._get_returns_data(symbols, period_days)
        if returns_data.empty:
            return None, []
            
        # Calculate risk metrics
        risk_metrics = self._calculate_risk_metrics(returns_data, weights, symbols)
        
        # Generate risk alerts
        alerts = self._generate_risk_alerts(user_id, risk_metrics, portfolio_data, returns_data)
        
        return risk_metrics, alerts
        
    def assess_position_risks(self, user_id: int, period_days: int = 252) -> List[PositionRisk]:
        """Assess risk for individual positions"""
        
        portfolio_data = self._get_portfolio_data(user_id)
        if not portfolio_data:
            return []
            
        symbols = list(portfolio_data.keys())
        returns_data = self._get_returns_data(symbols, period_days)
        
        if returns_data.empty:
            return []
            
        position_risks = []
        
        # Calculate market returns for beta calculation
        market_returns = self._get_market_returns(period_days)
        
        for symbol in symbols:
            if symbol not in returns_data.columns:
                continue
                
            symbol_returns = returns_data[symbol].dropna()
            weight = portfolio_data[symbol]['weight']
            
            # Calculate position-specific metrics
            volatility = symbol_returns.std() * np.sqrt(252)
            
            # Beta calculation
            if not market_returns.empty and len(symbol_returns) > 1:
                aligned_returns = symbol_returns.align(market_returns, join='inner')
                symbol_aligned, market_aligned = aligned_returns
                
                if len(symbol_aligned) > 1 and market_aligned.var() > 0:
                    beta = np.cov(symbol_aligned, market_aligned)[0][1] / market_aligned.var()
                else:
                    beta = 1.0
            else:
                beta = 1.0
                
            # VaR contribution (simplified)
            var_contribution = weight * volatility * 1.65  # 95% confidence
            
            # Concentration score
            concentration_score = min(weight / self.risk_thresholds['max_position_weight'], 1.0)
            
            # Liquidity score (simplified based on volume)
            liquidity_score = self._calculate_liquidity_score(symbol)
            
            # Average correlation with other positions
            correlations = []
            for other_symbol in symbols:
                if other_symbol != symbol and other_symbol in returns_data.columns:
                    corr = returns_data[symbol].corr(returns_data[other_symbol])
                    if not np.isnan(corr):
                        correlations.append(abs(corr))
                        
            correlation_avg = np.mean(correlations) if correlations else 0.0
            
            position_risk = PositionRisk(
                symbol=symbol,
                weight=weight,
                volatility=volatility,
                beta=beta,
                var_contribution=var_contribution,
                concentration_score=concentration_score,
                liquidity_score=liquidity_score,
                correlation_avg=correlation_avg
            )
            
            position_risks.append(position_risk)
            
        return position_risks
        
    def calculate_var(self, returns: pd.Series, confidence_level: float = 0.95) -> float:
        """Calculate Value at Risk"""
        if returns.empty:
            return 0.0
            
        return np.percentile(returns, (1 - confidence_level) * 100)
        
    def calculate_expected_shortfall(self, returns: pd.Series, confidence_level: float = 0.95) -> float:
        """Calculate Expected Shortfall (Conditional VaR)"""
        if returns.empty:
            return 0.0
            
        var = self.calculate_var(returns, confidence_level)
        return returns[returns <= var].mean()
        
    def monte_carlo_var(self, returns_data: pd.DataFrame, weights: np.ndarray, 
                       num_simulations: int = 10000, time_horizon: int = 1) -> Dict[str, float]:
        """Monte Carlo VaR calculation"""
        
        if returns_data.empty or len(weights) == 0:
            return {'var_95': 0.0, 'var_99': 0.0, 'expected_shortfall': 0.0}
            
        # Calculate mean returns and covariance matrix
        mean_returns = returns_data.mean().values
        cov_matrix = returns_data.cov().values
        
        # Run Monte Carlo simulation
        simulated_returns = np.random.multivariate_normal(
            mean_returns * time_horizon, 
            cov_matrix * time_horizon, 
            num_simulations
        )
        
        # Calculate portfolio returns
        portfolio_returns = np.dot(simulated_returns, weights)
        
        # Calculate VaR metrics
        var_95 = np.percentile(portfolio_returns, 5)
        var_99 = np.percentile(portfolio_returns, 1)
        expected_shortfall = portfolio_returns[portfolio_returns <= var_95].mean()
        
        return {
            'var_95': var_95,
            'var_99': var_99,
            'expected_shortfall': expected_shortfall
        }
        
    def stress_test_portfolio(self, user_id: int, scenarios: List[Dict[str, float]]) -> Dict[str, Any]:
        """Stress test portfolio under various scenarios"""
        
        portfolio_data = self._get_portfolio_data(user_id)
        if not portfolio_data:
            return {}
            
        # Get current portfolio value
        current_value = sum(data['market_value'] for data in portfolio_data.values())
        
        stress_results = []
        
        for i, scenario in enumerate(scenarios):
            scenario_name = scenario.get('name', f'Scenario {i+1}')
            scenario_description = scenario.get('description', '')
            
            # Calculate portfolio impact
            portfolio_impact = 0.0
            detailed_impacts = {}
            
            for symbol, data in portfolio_data.items():
                symbol_impact = scenario.get(symbol, scenario.get('market', 0.0))
                position_impact = data['market_value'] * symbol_impact
                portfolio_impact += position_impact
                detailed_impacts[symbol] = {
                    'impact_percent': symbol_impact,
                    'impact_value': position_impact,
                    'weight': data['weight']
                }
                
            new_value = current_value + portfolio_impact
            total_impact_percent = portfolio_impact / current_value if current_value > 0 else 0
            
            stress_results.append({
                'scenario_name': scenario_name,
                'scenario_description': scenario_description,
                'current_value': current_value,
                'new_value': new_value,
                'impact_value': portfolio_impact,
                'impact_percent': total_impact_percent,
                'detailed_impacts': detailed_impacts
            })
            
        return {
            'user_id': user_id,
            'current_portfolio_value': current_value,
            'stress_test_results': stress_results,
            'worst_case_scenario': min(stress_results, key=lambda x: x['impact_percent']),
            'best_case_scenario': max(stress_results, key=lambda x: x['impact_percent'])
        }
        
    def check_risk_limits(self, user_id: int) -> List[RiskAlert]:
        """Check portfolio against risk limits"""
        
        alerts = []
        portfolio_data = self._get_portfolio_data(user_id)
        
        if not portfolio_data:
            return alerts
            
        # Check concentration limits
        for symbol, data in portfolio_data.items():
            weight = data['weight']
            
            if weight > self.risk_thresholds['max_position_weight']:
                alerts.append(RiskAlert(
                    risk_type=RiskType.CONCENTRATION,
                    level=RiskLevel.HIGH if weight > 0.3 else RiskLevel.MEDIUM,
                    message=f"Position {symbol} exceeds concentration limit ({weight:.1%} vs {self.risk_thresholds['max_position_weight']:.1%})",
                    value=weight,
                    threshold=self.risk_thresholds['max_position_weight'],
                    recommendation=f"Consider reducing {symbol} position or diversifying",
                    created_at=datetime.now(),
                    user_id=user_id,
                    symbol=symbol
                ))
                
        # Check sector concentration (simplified)
        sector_weights = self._calculate_sector_weights(portfolio_data)
        for sector, weight in sector_weights.items():
            if weight > self.risk_thresholds['max_sector_weight']:
                alerts.append(RiskAlert(
                    risk_type=RiskType.CONCENTRATION,
                    level=RiskLevel.MEDIUM,
                    message=f"Sector {sector} exceeds concentration limit ({weight:.1%})",
                    value=weight,
                    threshold=self.risk_thresholds['max_sector_weight'],
                    recommendation=f"Consider diversifying away from {sector} sector",
                    created_at=datetime.now(),
                    user_id=user_id
                ))
                
        return alerts
        
    def _get_portfolio_data(self, user_id: int) -> Dict[str, Dict[str, float]]:
        """Get current portfolio data"""
        
        # Get user's accounts
        accounts = self.db.query(Account).filter(
            Account.user_id == user_id,
            Account.account_type.in_(['investment', 'retirement'])
        ).all()
        
        portfolio_data = {}
        total_value = 0.0
        
        for account in accounts:
            holdings = self.db.query(Holding).filter(Holding.account_id == account.id).all()
            
            for holding in holdings:
                if holding.symbol and holding.market_value:
                    if holding.symbol not in portfolio_data:
                        portfolio_data[holding.symbol] = {
                            'market_value': 0.0,
                            'quantity': 0.0
                        }
                        
                    portfolio_data[holding.symbol]['market_value'] += holding.market_value
                    portfolio_data[holding.symbol]['quantity'] += holding.quantity
                    total_value += holding.market_value
                    
        # Calculate weights
        for symbol in portfolio_data:
            portfolio_data[symbol]['weight'] = (
                portfolio_data[symbol]['market_value'] / total_value if total_value > 0 else 0
            )
            
        return portfolio_data
        
    def _get_returns_data(self, symbols: List[str], period_days: int) -> pd.DataFrame:
        """Get historical returns data"""
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=period_days + 30)  # Extra buffer
        
        try:
            # Use yfinance to get historical data
            data = yf.download(symbols, start=start_date, end=end_date, progress=False)
            
            if len(symbols) == 1:
                prices = data[['Adj Close']].rename(columns={'Adj Close': symbols[0]})
            else:
                prices = data['Adj Close']
                
            # Calculate returns
            returns = prices.pct_change().dropna()
            return returns.iloc[-period_days:]  # Get last period_days returns
            
        except Exception as e:
            logger.error(f"Failed to get returns data: {e}")
            return pd.DataFrame()
            
    def _get_market_returns(self, period_days: int) -> pd.Series:
        """Get market (SPY) returns for beta calculation"""
        
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=period_days + 30)
            
            spy_data = yf.download('SPY', start=start_date, end=end_date, progress=False)
            returns = spy_data['Adj Close'].pct_change().dropna()
            return returns.iloc[-period_days:]
            
        except Exception as e:
            logger.error(f"Failed to get market returns: {e}")
            return pd.Series()
            
    def _calculate_risk_metrics(self, returns_data: pd.DataFrame, weights: np.ndarray, symbols: List[str]) -> RiskMetrics:
        """Calculate comprehensive risk metrics"""
        
        # Portfolio returns
        portfolio_returns = (returns_data * weights).sum(axis=1)
        
        # VaR calculations
        var_95 = self.calculate_var(portfolio_returns, 0.95)
        var_99 = self.calculate_var(portfolio_returns, 0.99)
        expected_shortfall = self.calculate_expected_shortfall(portfolio_returns, 0.95)
        
        # Volatility
        volatility = portfolio_returns.std() * np.sqrt(252)
        
        # Max drawdown
        cumulative_returns = (1 + portfolio_returns).cumprod()
        rolling_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - rolling_max) / rolling_max
        max_drawdown = drawdown.min()
        
        # Beta (vs market)
        market_returns = self._get_market_returns(len(portfolio_returns))
        if not market_returns.empty and len(portfolio_returns) > 1:
            aligned_returns = portfolio_returns.align(market_returns, join='inner')
            portfolio_aligned, market_aligned = aligned_returns
            
            if len(portfolio_aligned) > 1 and market_aligned.var() > 0:
                beta = np.cov(portfolio_aligned, market_aligned)[0][1] / market_aligned.var()
                tracking_error = (portfolio_aligned - market_aligned).std() * np.sqrt(252)
                information_ratio = (portfolio_aligned - market_aligned).mean() * 252 / tracking_error if tracking_error > 0 else 0
            else:
                beta = 1.0
                tracking_error = 0.0
                information_ratio = 0.0
        else:
            beta = 1.0
            tracking_error = 0.0
            information_ratio = 0.0
            
        # Concentration risk (Herfindahl index)
        concentration_risk = np.sum(weights ** 2)
        
        # Correlation risk (average pairwise correlation)
        if returns_data.shape[1] > 1:
            corr_matrix = returns_data.corr()
            # Get upper triangle of correlation matrix (excluding diagonal)
            mask = np.triu(np.ones_like(corr_matrix), k=1).astype(bool)
            correlations = corr_matrix.values[mask]
            correlation_risk = np.mean(np.abs(correlations[~np.isnan(correlations)]))
        else:
            correlation_risk = 0.0
            
        # Liquidity score (simplified)
        liquidity_scores = [self._calculate_liquidity_score(symbol) for symbol in symbols]
        liquidity_score = np.average(liquidity_scores, weights=weights)
        
        return RiskMetrics(
            var_95=var_95,
            var_99=var_99,
            expected_shortfall=expected_shortfall,
            max_drawdown=max_drawdown,
            volatility=volatility,
            beta=beta,
            tracking_error=tracking_error,
            information_ratio=information_ratio,
            concentration_risk=concentration_risk,
            correlation_risk=correlation_risk,
            liquidity_score=liquidity_score
        )
        
    def _calculate_liquidity_score(self, symbol: str) -> float:
        """Calculate liquidity score for a symbol (simplified)"""
        
        try:
            # Get recent volume data
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1mo")
            
            if hist.empty:
                return 0.5  # Default medium liquidity
                
            avg_volume = hist['Volume'].mean()
            
            # Simple liquidity scoring based on volume
            # This is very simplified - real liquidity analysis is more complex
            if avg_volume > 1000000:  # High volume
                return 0.9
            elif avg_volume > 100000:  # Medium volume
                return 0.7
            elif avg_volume > 10000:   # Low volume
                return 0.4
            else:                      # Very low volume
                return 0.2
                
        except Exception:
            return 0.5  # Default
            
    def _calculate_sector_weights(self, portfolio_data: Dict[str, Dict[str, float]]) -> Dict[str, float]:
        """Calculate sector weights (simplified)"""
        
        # This is a simplified sector mapping
        # In practice, you'd use a comprehensive sector database
        sector_mapping = {
            'AAPL': 'Technology', 'MSFT': 'Technology', 'GOOGL': 'Technology', 'AMZN': 'Consumer Discretionary',
            'TSLA': 'Consumer Discretionary', 'META': 'Technology', 'NVDA': 'Technology',
            'JPM': 'Financials', 'BAC': 'Financials', 'WFC': 'Financials',
            'JNJ': 'Healthcare', 'UNH': 'Healthcare', 'PFE': 'Healthcare',
            'XOM': 'Energy', 'CVX': 'Energy', 'COP': 'Energy'
        }
        
        sector_weights = {}
        
        for symbol, data in portfolio_data.items():
            sector = sector_mapping.get(symbol, 'Other')
            if sector not in sector_weights:
                sector_weights[sector] = 0.0
            sector_weights[sector] += data['weight']
            
        return sector_weights
        
    def _generate_risk_alerts(self, user_id: int, risk_metrics: RiskMetrics, 
                            portfolio_data: Dict[str, Dict[str, float]], 
                            returns_data: pd.DataFrame) -> List[RiskAlert]:
        """Generate risk alerts based on metrics"""
        
        alerts = []
        
        # VaR alert
        if abs(risk_metrics.var_95) > self.risk_thresholds['max_portfolio_var']:
            alerts.append(RiskAlert(
                risk_type=RiskType.MARKET,
                level=RiskLevel.HIGH,
                message=f"Portfolio VaR exceeds limit ({risk_metrics.var_95:.2%} vs {self.risk_thresholds['max_portfolio_var']:.2%})",
                value=abs(risk_metrics.var_95),
                threshold=self.risk_thresholds['max_portfolio_var'],
                recommendation="Consider reducing position sizes or adding hedging instruments",
                created_at=datetime.now(),
                user_id=user_id
            ))
            
        # Volatility alert
        if risk_metrics.volatility > self.risk_thresholds['max_volatility']:
            alerts.append(RiskAlert(
                risk_type=RiskType.VOLATILITY,
                level=RiskLevel.MEDIUM,
                message=f"Portfolio volatility is high ({risk_metrics.volatility:.1%})",
                value=risk_metrics.volatility,
                threshold=self.risk_thresholds['max_volatility'],
                recommendation="Consider adding less volatile assets or reducing position sizes",
                created_at=datetime.now(),
                user_id=user_id
            ))
            
        # Concentration alert
        if risk_metrics.concentration_risk > 0.3:  # High concentration
            alerts.append(RiskAlert(
                risk_type=RiskType.CONCENTRATION,
                level=RiskLevel.MEDIUM,
                message="Portfolio shows high concentration risk",
                value=risk_metrics.concentration_risk,
                threshold=0.3,
                recommendation="Consider diversifying across more positions",
                created_at=datetime.now(),
                user_id=user_id
            ))
            
        # Correlation alert
        if risk_metrics.correlation_risk > self.risk_thresholds['max_correlation']:
            alerts.append(RiskAlert(
                risk_type=RiskType.CORRELATION,
                level=RiskLevel.MEDIUM,
                message=f"High correlation between portfolio positions ({risk_metrics.correlation_risk:.1%})",
                value=risk_metrics.correlation_risk,
                threshold=self.risk_thresholds['max_correlation'],
                recommendation="Consider adding uncorrelated assets",
                created_at=datetime.now(),
                user_id=user_id
            ))
            
        # Liquidity alert
        if risk_metrics.liquidity_score < self.risk_thresholds['min_liquidity_score']:
            alerts.append(RiskAlert(
                risk_type=RiskType.LIQUIDITY,
                level=RiskLevel.MEDIUM,
                message=f"Portfolio liquidity is low ({risk_metrics.liquidity_score:.1f})",
                value=risk_metrics.liquidity_score,
                threshold=self.risk_thresholds['min_liquidity_score'],
                recommendation="Consider replacing illiquid positions with more liquid alternatives",
                created_at=datetime.now(),
                user_id=user_id
            ))
            
        return alerts