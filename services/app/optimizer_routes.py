from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Dict, List, Optional
from .database import get_db
from .optimizer import PortfolioOptimizer
from pydantic import BaseModel

router = APIRouter(prefix="/optimizer", tags=["optimizer"])


class OptimizationRequest(BaseModel):
    """Request model for portfolio optimization"""
    method: str = "max_sharpe"  # max_sharpe, min_volatility, max_return
    constraints: Optional[Dict] = None
    lookback_days: int = 252


class OptimizationResponse(BaseModel):
    """Response model for optimization results"""
    optimal_weights: Dict[str, float]
    expected_return: float
    expected_volatility: float
    sharpe_ratio: float
    current_weights: Dict[str, float]
    rebalance_trades: Dict[str, float]
    optimization_method: str


class EfficientFrontierResponse(BaseModel):
    """Response model for efficient frontier"""
    portfolios: List[Dict]


class RebalancingRecommendation(BaseModel):
    """Model for rebalancing recommendations"""
    strategy_name: str
    symbol: str
    action: str
    current_weight: float
    target_weight: float
    drift: float
    trade_value: float
    priority: str


class RebalancingResponse(BaseModel):
    """Response model for rebalancing recommendations"""
    recommendations: List[RebalancingRecommendation]


@router.post("/optimize/{user_id}", response_model=OptimizationResponse)
async def optimize_portfolio(
    user_id: int,
    request: OptimizationRequest,
    db: Session = Depends(get_db)
):
    """Optimize portfolio allocation using various methods"""
    
    optimizer = PortfolioOptimizer(db)
    result = optimizer.optimize_portfolio(
        user_id=user_id,
        method=request.method,
        constraints=request.constraints,
        lookback_days=request.lookback_days
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="Unable to optimize portfolio - insufficient data")
    
    return OptimizationResponse(
        optimal_weights=result.optimal_weights,
        expected_return=result.expected_return,
        expected_volatility=result.expected_volatility,
        sharpe_ratio=result.sharpe_ratio,
        current_weights=result.current_weights,
        rebalance_trades=result.rebalance_trades,
        optimization_method=result.optimization_method
    )


@router.get("/efficient-frontier/{user_id}", response_model=EfficientFrontierResponse)
async def get_efficient_frontier(
    user_id: int,
    n_portfolios: int = Query(50, description="Number of portfolios to generate"),
    db: Session = Depends(get_db)
):
    """Generate efficient frontier data points"""
    
    optimizer = PortfolioOptimizer(db)
    portfolios = optimizer.generate_efficient_frontier(user_id, n_portfolios)
    
    if not portfolios:
        raise HTTPException(status_code=404, detail="Unable to generate efficient frontier - insufficient data")
    
    return EfficientFrontierResponse(portfolios=portfolios)


@router.get("/rebalancing/{user_id}", response_model=RebalancingResponse)
async def get_rebalancing_recommendations(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Get rebalancing recommendations based on user's strategies"""
    
    optimizer = PortfolioOptimizer(db)
    recommendations = optimizer.get_rebalancing_recommendations(user_id)
    
    recommendations_models = [
        RebalancingRecommendation(
            strategy_name=rec['strategy_name'],
            symbol=rec['symbol'],
            action=rec['action'],
            current_weight=rec['current_weight'],
            target_weight=rec['target_weight'],
            drift=rec['drift'],
            trade_value=rec['trade_value'],
            priority=rec['priority']
        )
        for rec in recommendations
    ]
    
    return RebalancingResponse(recommendations=recommendations_models)


@router.get("/methods")
async def get_optimization_methods():
    """Get available optimization methods and their descriptions"""
    
    methods = [
        {
            "name": "max_sharpe",
            "display_name": "Maximum Sharpe Ratio",
            "description": "Optimize for the best risk-adjusted return"
        },
        {
            "name": "min_volatility",
            "display_name": "Minimum Volatility",
            "description": "Minimize portfolio risk (volatility)"
        },
        {
            "name": "max_return",
            "display_name": "Maximum Return",
            "description": "Maximize expected portfolio return"
        }
    ]
    
    return {"methods": methods}


@router.get("/constraints")
async def get_available_constraints():
    """Get available constraint types for optimization"""
    
    constraints = [
        {
            "name": "max_weight",
            "type": "float",
            "description": "Maximum weight for any single asset (0-1)",
            "default": 1.0
        },
        {
            "name": "min_weight",
            "type": "float",
            "description": "Minimum weight for any single asset (0-1)",
            "default": 0.0
        },
        {
            "name": "sector_limits",
            "type": "dict",
            "description": "Maximum allocation per sector",
            "default": {}
        }
    ]
    
    return {"constraints": constraints}


@router.post("/simulate/{user_id}")
async def simulate_optimization(
    user_id: int,
    request: OptimizationRequest,
    db: Session = Depends(get_db)
):
    """Simulate optimization without making changes"""
    
    optimizer = PortfolioOptimizer(db)
    result = optimizer.optimize_portfolio(
        user_id=user_id,
        method=request.method,
        constraints=request.constraints,
        lookback_days=request.lookback_days
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="Unable to simulate optimization")
    
    # Calculate trade details
    current_portfolio = optimizer._get_current_portfolio(user_id)
    total_value = sum(current_portfolio.values())
    
    trade_details = []
    for symbol, weight_change in result.rebalance_trades.items():
        if abs(weight_change) > 0.001:  # Only show significant trades
            trade_value = weight_change * total_value
            trade_details.append({
                "symbol": symbol,
                "action": "BUY" if trade_value > 0 else "SELL",
                "current_weight": result.current_weights.get(symbol, 0),
                "target_weight": result.optimal_weights.get(symbol, 0),
                "weight_change": weight_change,
                "trade_value": abs(trade_value)
            })
    
    return {
        "optimization_result": result.__dict__,
        "trade_details": trade_details,
        "total_portfolio_value": total_value,
        "number_of_trades": len(trade_details)
    }