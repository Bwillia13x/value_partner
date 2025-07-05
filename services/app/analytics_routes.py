from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import Dict, List
from datetime import datetime, timedelta
from .database import get_db, User
from .auth_routes import get_current_user
from .analytics import PortfolioAnalytics
from pydantic import BaseModel

router = APIRouter(prefix="/analytics", tags=["analytics"])


class PerformanceResponse(BaseModel):
    """Response model for performance metrics"""
    total_return: float
    annualized_return: float
    volatility: float
    sharpe_ratio: float
    max_drawdown: float
    current_value: float
    benchmark_return: float
    alpha: float
    beta: float


class PerformanceTimeSeriesResponse(BaseModel):
    """Response model for performance time series"""
    dates: List[str]
    portfolio_values: List[float]
    daily_returns: List[float]


class AssetAllocationResponse(BaseModel):
    """Response model for asset allocation"""
    allocation: Dict[str, float]
    total_value: float


class PerformanceAttributionResponse(BaseModel):
    """Response model for performance attribution"""
    contributions: Dict[str, float]


@router.get("/performance/{user_id}", response_model=PerformanceResponse)
async def get_portfolio_performance(
    user_id: int,
    period_days: int = Query(365, description="Analysis period in days"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get comprehensive portfolio performance metrics"""
    
    if user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    analytics = PortfolioAnalytics(db)
    metrics = analytics.calculate_performance_metrics(user_id, period_days)
    
    if not metrics:
        raise HTTPException(status_code=404, detail="No performance data found")
    
    return PerformanceResponse(
        total_return=metrics.total_return,
        annualized_return=metrics.annualized_return,
        volatility=metrics.volatility,
        sharpe_ratio=metrics.sharpe_ratio,
        max_drawdown=metrics.max_drawdown,
        current_value=metrics.current_value,
        benchmark_return=metrics.benchmark_return,
        alpha=metrics.alpha,
        beta=metrics.beta
    )


@router.get("/performance/{user_id}/timeseries", response_model=PerformanceTimeSeriesResponse)
async def get_portfolio_timeseries(
    user_id: int,
    period_days: int = Query(365, description="Analysis period in days"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get portfolio performance time series data"""
    
    if user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    analytics = PortfolioAnalytics(db)
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=period_days)
    
    returns_df = analytics.calculate_portfolio_returns(user_id, start_date, end_date)
    
    if returns_df.empty:
        raise HTTPException(status_code=404, detail="No time series data found")
    
    return PerformanceTimeSeriesResponse(
        dates=[d.strftime("%Y-%m-%d") for d in returns_df['date']],
        portfolio_values=returns_df['portfolio_value'].tolist(),
        daily_returns=returns_df['daily_return'].fillna(0).tolist()
    )


@router.get("/allocation/{user_id}", response_model=AssetAllocationResponse)
async def get_asset_allocation(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get current asset allocation breakdown"""
    
    if user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    analytics = PortfolioAnalytics(db)
    allocation = analytics.get_asset_allocation(user_id)
    total_value = analytics.get_current_portfolio_value(user_id)
    
    return AssetAllocationResponse(
        allocation=allocation,
        total_value=total_value
    )


@router.get("/attribution/{user_id}", response_model=PerformanceAttributionResponse)
async def get_performance_attribution(
    user_id: int,
    period_days: int = Query(30, description="Attribution period in days"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get performance attribution by security"""
    
    if user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    analytics = PortfolioAnalytics(db)
    attribution = analytics.get_performance_attribution(user_id, period_days)
    
    return PerformanceAttributionResponse(
        contributions=attribution
    )


@router.get("/summary/{user_id}")
async def get_analytics_summary(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get comprehensive analytics summary"""
    
    if user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    analytics = PortfolioAnalytics(db)
    
    # Get performance metrics
    metrics = analytics.calculate_performance_metrics(user_id)
    
    # Get current allocation
    allocation = analytics.get_asset_allocation(user_id)
    
    # Get performance attribution
    attribution = analytics.get_performance_attribution(user_id)
    
    return {
        "performance": metrics.__dict__ if metrics else None,
        "allocation": allocation,
        "attribution": attribution,
        "updated_at": datetime.now().isoformat()
    }


@router.get("/benchmarks")
async def get_available_benchmarks():
    """Get list of available benchmarks for comparison"""
    
    benchmarks = [
        {"symbol": "SPY", "name": "S&P 500 ETF", "category": "US Large Cap"},
        {"symbol": "QQQ", "name": "Nasdaq 100 ETF", "category": "US Tech"},
        {"symbol": "IWM", "name": "Russell 2000 ETF", "category": "US Small Cap"},
        {"symbol": "VTI", "name": "Total Stock Market ETF", "category": "US Total Market"},
        {"symbol": "VTIAX", "name": "Total International Stock", "category": "International"},
        {"symbol": "BND", "name": "Total Bond Market ETF", "category": "US Bonds"},
        {"symbol": "VNQ", "name": "Real Estate ETF", "category": "REITs"}
    ]
    
    return {"benchmarks": benchmarks}


@router.get("/risk-metrics/{user_id}")
async def get_risk_metrics(
    user_id: int,
    period_days: int = Query(365, description="Analysis period in days"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed risk metrics for the portfolio"""
    
    if user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    analytics = PortfolioAnalytics(db)
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=period_days)
    
    returns_df = analytics.calculate_portfolio_returns(user_id, start_date, end_date)
    
    if returns_df.empty:
        raise HTTPException(status_code=404, detail="No data available for risk analysis")
    
    returns = returns_df['daily_return'].dropna()
    
    # Calculate additional risk metrics
    var_95 = returns.quantile(0.05)  # 5% VaR
    var_99 = returns.quantile(0.01)  # 1% VaR
    
    # Expected shortfall (conditional VaR)
    es_95 = returns[returns <= var_95].mean()
    es_99 = returns[returns <= var_99].mean()
    
    # Skewness and kurtosis
    skewness = returns.skew()
    kurtosis = returns.kurtosis()
    
    return {
        "value_at_risk": {
            "var_95": var_95,
            "var_99": var_99,
            "expected_shortfall_95": es_95,
            "expected_shortfall_99": es_99
        },
        "distribution_metrics": {
            "skewness": skewness,
            "kurtosis": kurtosis
        },
        "period_days": period_days,
        "updated_at": datetime.now().isoformat()
    }