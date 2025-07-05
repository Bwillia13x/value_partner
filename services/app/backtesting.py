import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
from sqlalchemy.orm import Session

from .database import Strategy, StrategyHolding

logger = logging.getLogger(__name__)

class RebalancingFrequency(Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"

@dataclass
class BacktestConfig:
    """Configuration for backtesting"""
    start_date: datetime
    end_date: datetime
    initial_capital: float = 100000.0
    rebalancing_frequency: RebalancingFrequency = RebalancingFrequency.MONTHLY
    rebalancing_threshold: float = 0.05  # 5% drift threshold
    transaction_cost: float = 0.001  # 0.1% transaction cost
    benchmark_symbol: str = "SPY"
    include_dividends: bool = True
    
@dataclass
class BacktestResult:
    """Results from backtesting"""
    config: BacktestConfig
    portfolio_returns: pd.Series
    benchmark_returns: pd.Series
    portfolio_values: pd.Series
    benchmark_values: pd.Series
    weights_history: pd.DataFrame
    rebalancing_dates: List[datetime]
    transaction_costs: pd.Series
    
    # Performance metrics
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    
    # Benchmark comparison
    benchmark_total_return: float
    benchmark_annualized_return: float
    benchmark_volatility: float
    benchmark_sharpe_ratio: float
    alpha: float
    beta: float
    
    # Additional metrics
    calmar_ratio: float
    sortino_ratio: float
    information_ratio: float
    tracking_error: float
    
class PortfolioBacktester:
    """Portfolio backtesting engine"""
    
    def __init__(self, db: Session):
        self.db = db
        
    def backtest_strategy(self, strategy_id: int, config: BacktestConfig) -> BacktestResult:
        """Backtest a specific strategy"""
        
        # Get strategy from database
        strategy = self.db.query(Strategy).filter(Strategy.id == strategy_id).first()
        if not strategy:
            raise ValueError(f"Strategy {strategy_id} not found")
            
        # Get target allocation
        holdings = self.db.query(StrategyHolding).filter(
            StrategyHolding.strategy_id == strategy_id
        ).all()
        
        if not holdings:
            raise ValueError(f"No holdings found for strategy {strategy_id}")
            
        target_weights = {holding.symbol: holding.target_weight for holding in holdings}
        
        return self.backtest_allocation(target_weights, config)
        
    def backtest_allocation(self, target_weights: Dict[str, float], 
                          config: BacktestConfig) -> BacktestResult:
        """Backtest a specific allocation"""
        
        logger.info(f"Starting backtest from {config.start_date} to {config.end_date}")
        
        # Download price data
        symbols = list(target_weights.keys())
        price_data = self._download_price_data(symbols + [config.benchmark_symbol], 
                                             config.start_date, config.end_date)
        
        if price_data.empty:
            raise ValueError("No price data available for the specified period")
            
        # Calculate returns
        returns_data = price_data.pct_change().dropna()
        
        # Get rebalancing dates
        rebalancing_dates = self._get_rebalancing_dates(
            config.start_date, config.end_date, config.rebalancing_frequency
        )
        
        # Initialize portfolio
        portfolio_values = []
        weights_history = []
        transaction_costs = []
        current_weights = target_weights.copy()
        cash = config.initial_capital
        portfolio_value = config.initial_capital
        
        # Track actual holdings (shares)
        holdings = {symbol: 0.0 for symbol in symbols}
        
        for date in returns_data.index:
            daily_returns = returns_data.loc[date, symbols]
            
            # Check if we need to rebalance
            is_rebalancing_date = date.date() in [d.date() for d in rebalancing_dates]
            needs_threshold_rebalance = self._check_rebalancing_threshold(
                current_weights, target_weights, config.rebalancing_threshold
            )
            
            if is_rebalancing_date or needs_threshold_rebalance or date == returns_data.index[0]:
                # Rebalance portfolio
                cost = self._rebalance_portfolio(
                    holdings, target_weights, price_data.loc[date, symbols], 
                    portfolio_value, config.transaction_cost
                )
                transaction_costs.append(cost)
                cash -= cost
            else:
                transaction_costs.append(0.0)
            
            # Update portfolio value based on price changes
            if date != returns_data.index[0]:  # Skip first day
                for symbol in symbols:
                    if symbol in daily_returns:
                        holdings[symbol] *= (1 + daily_returns[symbol])
                        
            # Calculate current portfolio value
            portfolio_value = sum(
                holdings[symbol] * price_data.loc[date, symbol] 
                for symbol in symbols if symbol in price_data.columns
            ) + cash
            
            # Update current weights
            if portfolio_value > 0:
                current_weights = {
                    symbol: (holdings[symbol] * price_data.loc[date, symbol]) / portfolio_value
                    for symbol in symbols if symbol in price_data.columns
                }
            
            portfolio_values.append(portfolio_value)
            weights_history.append(current_weights.copy())
        
        # Convert to pandas series/dataframes
        portfolio_values = pd.Series(portfolio_values, index=returns_data.index)
        weights_history_df = pd.DataFrame(weights_history, index=returns_data.index)
        transaction_costs_series = pd.Series(transaction_costs, index=returns_data.index)
        
        # Calculate portfolio returns
        portfolio_returns = portfolio_values.pct_change().dropna()
        
        # Get benchmark data
        benchmark_values = price_data[config.benchmark_symbol] * (config.initial_capital / price_data[config.benchmark_symbol].iloc[0])
        benchmark_returns = benchmark_values.pct_change().dropna()
        
        # Calculate performance metrics
        metrics = self._calculate_performance_metrics(
            portfolio_returns, benchmark_returns, portfolio_values, 
            benchmark_values, transaction_costs_series
        )
        
        return BacktestResult(
            config=config,
            portfolio_returns=portfolio_returns,
            benchmark_returns=benchmark_returns,
            portfolio_values=portfolio_values,
            benchmark_values=benchmark_values,
            weights_history=weights_history_df,
            rebalancing_dates=rebalancing_dates,
            transaction_costs=transaction_costs_series,
            **metrics
        )
        
    def compare_strategies(self, strategy_configs: List[Tuple[Dict[str, float], str]], 
                         config: BacktestConfig) -> Dict[str, BacktestResult]:
        """Compare multiple strategies"""
        
        results = {}
        
        for target_weights, name in strategy_configs:
            try:
                result = self.backtest_allocation(target_weights, config)
                results[name] = result
                logger.info(f"Completed backtest for {name}")
            except Exception as e:
                logger.error(f"Failed to backtest {name}: {e}")
                
        return results
        
    def monte_carlo_simulation(self, target_weights: Dict[str, float], 
                             config: BacktestConfig, num_simulations: int = 1000) -> Dict:
        """Run Monte Carlo simulation for portfolio"""
        
        logger.info(f"Running Monte Carlo simulation with {num_simulations} trials")
        
        # Download historical data for return distribution
        symbols = list(target_weights.keys())
        price_data = self._download_price_data(symbols, 
                                             config.start_date - timedelta(days=365*2), 
                                             config.start_date)
        
        returns_data = price_data.pct_change().dropna()
        
        # Calculate mean returns and covariance matrix
        mean_returns = returns_data.mean()
        cov_matrix = returns_data.cov()
        
        # Run simulations
        simulation_results = []
        
        for i in range(num_simulations):
            # Generate random returns based on historical distribution
            simulated_returns = np.random.multivariate_normal(
                mean_returns, cov_matrix, len(returns_data)
            )
            
            # Calculate portfolio returns
            portfolio_returns = pd.DataFrame(simulated_returns, columns=symbols)
            weighted_returns = (portfolio_returns * pd.Series(target_weights)).sum(axis=1)
            
            # Calculate final value
            final_value = config.initial_capital * (1 + weighted_returns).prod()
            total_return = (final_value - config.initial_capital) / config.initial_capital
            
            simulation_results.append({
                'final_value': final_value,
                'total_return': total_return,
                'annual_return': (final_value / config.initial_capital) ** (252 / len(weighted_returns)) - 1
            })
        
        # Analyze results
        final_values = [r['final_value'] for r in simulation_results]
        total_returns = [r['total_return'] for r in simulation_results]
        annual_returns = [r['annual_return'] for r in simulation_results]
        
        return {
            'num_simulations': num_simulations,
            'mean_final_value': np.mean(final_values),
            'median_final_value': np.median(final_values),
            'std_final_value': np.std(final_values),
            'percentiles': {
                '5th': np.percentile(final_values, 5),
                '25th': np.percentile(final_values, 25),
                '75th': np.percentile(final_values, 75),
                '95th': np.percentile(final_values, 95)
            },
            'probability_positive': len([r for r in total_returns if r > 0]) / num_simulations,
            'probability_loss_10pct': len([r for r in total_returns if r < -0.1]) / num_simulations,
            'var_95': np.percentile(total_returns, 5),  # Value at Risk (95% confidence)
            'expected_shortfall': np.mean([r for r in total_returns if r <= np.percentile(total_returns, 5)])
        }
        
    def _download_price_data(self, symbols: List[str], start_date: datetime, 
                           end_date: datetime) -> pd.DataFrame:
        """Download price data for symbols"""
        
        try:
            data = yf.download(symbols, start=start_date, end=end_date, 
                             progress=False, group_by='ticker')
            
            if len(symbols) == 1:
                return data[['Adj Close']].rename(columns={'Adj Close': symbols[0]})
            else:
                # Extract adjusted close prices
                adj_close_data = {}
                for symbol in symbols:
                    try:
                        if symbol in data.columns.levels[0]:
                            adj_close_data[symbol] = data[symbol]['Adj Close']
                    except (KeyError, AttributeError):
                        logger.warning(f"Could not get data for {symbol}")
                        
                return pd.DataFrame(adj_close_data)
                
        except Exception as e:
            logger.error(f"Failed to download price data: {e}")
            return pd.DataFrame()
            
    def _get_rebalancing_dates(self, start_date: datetime, end_date: datetime, 
                             frequency: RebalancingFrequency) -> List[datetime]:
        """Get rebalancing dates based on frequency"""
        
        dates = []
        current_date = start_date
        
        while current_date <= end_date:
            dates.append(current_date)
            
            if frequency == RebalancingFrequency.DAILY:
                current_date += timedelta(days=1)
            elif frequency == RebalancingFrequency.WEEKLY:
                current_date += timedelta(weeks=1)
            elif frequency == RebalancingFrequency.MONTHLY:
                # Add approximately one month
                if current_date.month == 12:
                    current_date = current_date.replace(year=current_date.year + 1, month=1)
                else:
                    current_date = current_date.replace(month=current_date.month + 1)
            elif frequency == RebalancingFrequency.QUARTERLY:
                # Add 3 months
                for _ in range(3):
                    if current_date.month == 12:
                        current_date = current_date.replace(year=current_date.year + 1, month=1)
                    else:
                        current_date = current_date.replace(month=current_date.month + 1)
            elif frequency == RebalancingFrequency.ANNUAL:
                current_date = current_date.replace(year=current_date.year + 1)
                
        return dates
        
    def _check_rebalancing_threshold(self, current_weights: Dict[str, float], 
                                   target_weights: Dict[str, float], 
                                   threshold: float) -> bool:
        """Check if portfolio has drifted beyond threshold"""
        
        for symbol in target_weights:
            current_weight = current_weights.get(symbol, 0)
            target_weight = target_weights[symbol]
            drift = abs(current_weight - target_weight)
            
            if drift > threshold:
                return True
                
        return False
        
    def _rebalance_portfolio(self, holdings: Dict[str, float], 
                           target_weights: Dict[str, float], 
                           prices: pd.Series, portfolio_value: float, 
                           transaction_cost: float) -> float:
        """Rebalance portfolio to target weights"""
        
        total_cost = 0.0
        
        for symbol in target_weights:
            if symbol not in prices:
                continue
                
            target_value = portfolio_value * target_weights[symbol]
            target_shares = target_value / prices[symbol]
            current_shares = holdings.get(symbol, 0)
            
            # Calculate trade
            shares_to_trade = target_shares - current_shares
            trade_value = abs(shares_to_trade * prices[symbol])
            
            # Apply transaction cost
            cost = trade_value * transaction_cost
            total_cost += cost
            
            # Update holdings
            holdings[symbol] = target_shares
            
        return total_cost
        
    def _calculate_performance_metrics(self, portfolio_returns: pd.Series, 
                                     benchmark_returns: pd.Series,
                                     portfolio_values: pd.Series,
                                     benchmark_values: pd.Series,
                                     transaction_costs: pd.Series) -> Dict:
        """Calculate comprehensive performance metrics"""
        
        # Align series
        aligned_returns = portfolio_returns.align(benchmark_returns, join='inner')
        portfolio_returns, benchmark_returns = aligned_returns
        
        # Basic metrics
        total_return = (portfolio_values.iloc[-1] - portfolio_values.iloc[0]) / portfolio_values.iloc[0]
        benchmark_total_return = (benchmark_values.iloc[-1] - benchmark_values.iloc[0]) / benchmark_values.iloc[0]
        
        days = len(portfolio_returns)
        annualized_return = (1 + total_return) ** (252 / days) - 1
        benchmark_annualized_return = (1 + benchmark_total_return) ** (252 / days) - 1
        
        # Risk metrics
        volatility = portfolio_returns.std() * np.sqrt(252)
        benchmark_volatility = benchmark_returns.std() * np.sqrt(252)
        
        # Sharpe ratio (assuming 2% risk-free rate)
        risk_free_rate = 0.02
        sharpe_ratio = (annualized_return - risk_free_rate) / volatility if volatility > 0 else 0
        benchmark_sharpe_ratio = (benchmark_annualized_return - risk_free_rate) / benchmark_volatility if benchmark_volatility > 0 else 0
        
        # Drawdown
        rolling_max = portfolio_values.expanding().max()
        drawdown = (portfolio_values - rolling_max) / rolling_max
        max_drawdown = drawdown.min()
        
        # Alpha and Beta
        if len(portfolio_returns) > 1 and len(benchmark_returns) > 1:
            covariance = np.cov(portfolio_returns, benchmark_returns)[0][1]
            benchmark_variance = np.var(benchmark_returns)
            beta = covariance / benchmark_variance if benchmark_variance > 0 else 0
            alpha = annualized_return - (risk_free_rate + beta * (benchmark_annualized_return - risk_free_rate))
        else:
            beta = 0
            alpha = 0
            
        # Additional metrics
        calmar_ratio = abs(annualized_return / max_drawdown) if max_drawdown < 0 else 0
        
        # Sortino ratio (downside deviation)
        downside_returns = portfolio_returns[portfolio_returns < 0]
        downside_deviation = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 0
        sortino_ratio = (annualized_return - risk_free_rate) / downside_deviation if downside_deviation > 0 else 0
        
        # Information ratio and tracking error
        excess_returns = portfolio_returns - benchmark_returns
        tracking_error = excess_returns.std() * np.sqrt(252)
        information_ratio = excess_returns.mean() * 252 / tracking_error if tracking_error > 0 else 0
        
        return {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'volatility': volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'benchmark_total_return': benchmark_total_return,
            'benchmark_annualized_return': benchmark_annualized_return,
            'benchmark_volatility': benchmark_volatility,
            'benchmark_sharpe_ratio': benchmark_sharpe_ratio,
            'alpha': alpha,
            'beta': beta,
            'calmar_ratio': calmar_ratio,
            'sortino_ratio': sortino_ratio,
            'information_ratio': information_ratio,
            'tracking_error': tracking_error
        }