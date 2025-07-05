import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from .database import Account, Holding, Transaction, TransactionType
import yfinance as yf
from dataclasses import dataclass


@dataclass
class PerformanceMetrics:
    """Data class for portfolio performance metrics"""
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    current_value: float
    benchmark_return: float
    alpha: float
    beta: float


class PortfolioAnalytics:
    """Advanced portfolio analytics and performance calculations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def calculate_portfolio_returns(self, user_id: int, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Calculate daily portfolio returns for a user"""
        
        # Get all investment accounts for the user
        accounts = self.db.query(Account).filter(
            Account.user_id == user_id,
            Account.account_type.in_(['investment', 'retirement'])
        ).all()
        
        if not accounts:
            return pd.DataFrame()
        
        account_ids = [acc.id for acc in accounts]
        
        # Get historical transactions for portfolio value calculation
        transactions = self.db.query(Transaction).filter(
            Transaction.account_id.in_(account_ids),
            Transaction.date >= start_date,
            Transaction.date <= end_date,
            Transaction.transaction_type.in_([TransactionType.PURCHASE, TransactionType.SALE])
        ).order_by(Transaction.date).all()
        
        # Convert to DataFrame for easier manipulation
        df_transactions = pd.DataFrame([{
            'date': t.date,
            'symbol': t.symbol,
            'quantity': t.quantity if t.transaction_type == TransactionType.PURCHASE else -t.quantity,
            'amount': t.amount if t.transaction_type == TransactionType.PURCHASE else -t.amount
        } for t in transactions if t.symbol])
        
        if df_transactions.empty:
            return pd.DataFrame()
        
        # Calculate daily portfolio values
        return self._calculate_daily_portfolio_values(df_transactions, start_date, end_date)
    
    def _calculate_daily_portfolio_values(self, transactions_df: pd.DataFrame, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Calculate daily portfolio values from transactions"""
        
        # Get unique symbols
        symbols = transactions_df['symbol'].unique()
        
        # Download historical price data
        price_data = {}
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(start=start_date, end=end_date + timedelta(days=1))
                price_data[symbol] = hist['Close']
            except Exception as e:
                print(f"Error fetching data for {symbol}: {e}")
                continue
        
        if not price_data:
            return pd.DataFrame()
        
        # Create date range
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        
        # Calculate daily portfolio values
        portfolio_values = []
        
        for date in date_range:
            total_value = 0
            
            # Calculate cumulative positions up to this date
            for symbol in symbols:
                symbol_transactions = transactions_df[
                    (transactions_df['symbol'] == symbol) & 
                    (transactions_df['date'] <= date)
                ]
                
                if symbol_transactions.empty or symbol not in price_data:
                    continue
                
                # Calculate total shares held
                total_shares = symbol_transactions['quantity'].sum()
                
                if total_shares > 0:
                    # Get price for this date
                    try:
                        price = price_data[symbol].asof(date)
                        if pd.notna(price):
                            total_value += total_shares * price
                    except (KeyError, IndexError):
                        continue
            
            portfolio_values.append({
                'date': date,
                'portfolio_value': total_value
            })
        
        df_portfolio = pd.DataFrame(portfolio_values)
        
        # Calculate daily returns
        df_portfolio['daily_return'] = df_portfolio['portfolio_value'].pct_change()
        
        return df_portfolio
    
    def calculate_performance_metrics(self, user_id: int, period_days: int = 365) -> Optional[PerformanceMetrics]:
        """Calculate comprehensive performance metrics for a user's portfolio"""
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=period_days)
        
        # Get portfolio returns
        returns_df = self.calculate_portfolio_returns(user_id, start_date, end_date)
        
        if returns_df.empty:
            return None
        
        # Get current portfolio value
        current_value = self.get_current_portfolio_value(user_id)
        
        # Calculate metrics
        returns = returns_df['daily_return'].dropna()
        
        if len(returns) < 2:
            return None
        
        # Total return
        total_return = (returns_df['portfolio_value'].iloc[-1] / returns_df['portfolio_value'].iloc[0]) - 1
        
        # Annualized return
        days_in_period = len(returns)
        annualized_return = (1 + total_return) ** (365 / days_in_period) - 1
        
        # Volatility (annualized)
        volatility = returns.std() * np.sqrt(252)  # 252 trading days
        
        # Sharpe ratio (assuming 2% risk-free rate)
        risk_free_rate = 0.02
        sharpe_ratio = (annualized_return - risk_free_rate) / volatility if volatility > 0 else 0
        
        # Maximum drawdown
        cumulative_returns = (1 + returns).cumprod()
        rolling_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns - rolling_max) / rolling_max
        max_drawdown = drawdown.min()
        
        # Benchmark comparison (S&P 500)
        benchmark_return, alpha, beta = self._calculate_benchmark_metrics(returns, start_date, end_date)
        
        return PerformanceMetrics(
            total_return=total_return,
            annualized_return=annualized_return,
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            current_value=current_value,
            benchmark_return=benchmark_return,
            alpha=alpha,
            beta=beta
        )
    
    def _calculate_benchmark_metrics(self, portfolio_returns: pd.Series, start_date: datetime, end_date: datetime) -> Tuple[float, float, float]:
        """Calculate alpha and beta vs S&P 500"""
        
        try:
            # Get S&P 500 data
            spy = yf.Ticker("SPY")
            spy_data = spy.history(start=start_date, end=end_date + timedelta(days=1))
            spy_returns = spy_data['Close'].pct_change().dropna()
            
            # Align dates
            portfolio_returns = portfolio_returns.reset_index(drop=True)
            spy_returns = spy_returns.reset_index(drop=True)
            
            min_length = min(len(portfolio_returns), len(spy_returns))
            portfolio_returns = portfolio_returns.iloc[:min_length]
            spy_returns = spy_returns.iloc[:min_length]
            
            # Calculate benchmark return
            benchmark_return = (1 + spy_returns).prod() - 1
            
            # Calculate beta
            covariance = np.cov(portfolio_returns, spy_returns)[0, 1]
            benchmark_variance = np.var(spy_returns)
            beta = covariance / benchmark_variance if benchmark_variance > 0 else 0
            
            # Calculate alpha (annualized)
            portfolio_mean = portfolio_returns.mean() * 252
            benchmark_mean = spy_returns.mean() * 252
            risk_free_rate = 0.02
            alpha = portfolio_mean - risk_free_rate - beta * (benchmark_mean - risk_free_rate)
            
            return benchmark_return, alpha, beta
            
        except Exception as e:
            print(f"Error calculating benchmark metrics: {e}")
            return 0.0, 0.0, 1.0
    
    def get_current_portfolio_value(self, user_id: int) -> float:
        """Get current total portfolio value for a user"""
        
        # Get all investment accounts
        accounts = self.db.query(Account).filter(
            Account.user_id == user_id,
            Account.account_type.in_(['investment', 'retirement'])
        ).all()
        
        total_value = 0.0
        
        for account in accounts:
            # Get current holdings
            holdings = self.db.query(Holding).filter(Holding.account_id == account.id).all()
            
            for holding in holdings:
                total_value += holding.market_value
        
        return total_value
    
    def get_asset_allocation(self, user_id: int) -> Dict[str, float]:
        """Get current asset allocation breakdown"""
        
        accounts = self.db.query(Account).filter(
            Account.user_id == user_id,
            Account.account_type.in_(['investment', 'retirement'])
        ).all()
        
        allocation = {}
        total_value = 0.0
        
        for account in accounts:
            holdings = self.db.query(Holding).filter(Holding.account_id == account.id).all()
            
            for holding in holdings:
                security_type = holding.security_type or 'unknown'
                allocation[security_type] = allocation.get(security_type, 0) + holding.market_value
                total_value += holding.market_value
        
        # Convert to percentages
        if total_value > 0:
            allocation = {k: v / total_value for k, v in allocation.items()}
        
        return allocation
    
    def get_performance_attribution(self, user_id: int, period_days: int = 30) -> Dict[str, float]:
        """Calculate performance attribution by security"""
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=period_days)
        
        accounts = self.db.query(Account).filter(
            Account.user_id == user_id,
            Account.account_type.in_(['investment', 'retirement'])
        ).all()
        
        attribution = {}
        
        for account in accounts:
            holdings = self.db.query(Holding).filter(Holding.account_id == account.id).all()
            
            for holding in holdings:
                if holding.symbol and holding.cost_basis:
                    # Calculate contribution to total return
                    current_return = (holding.market_value - holding.cost_basis) / holding.cost_basis
                    weight = holding.market_value / self.get_current_portfolio_value(user_id)
                    contribution = current_return * weight
                    
                    attribution[holding.symbol] = contribution
        
        return attribution