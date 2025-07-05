from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from . import schemas
from .database import Strategy, Holding, StrategyHolding
from .database import get_db
from .rebalancer import Rebalancer
from .auth_routes import get_current_user
from .database import User


router = APIRouter(
    prefix="/strategies",
    tags=["strategies"],
)

@router.post("/", response_model=schemas.Strategy)
def create_strategy(
    strategy: schemas.StrategyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    holdings_data = strategy.holdings
    strategy_data = strategy.model_dump(exclude={'holdings'})

    db_strategy = Strategy(**strategy_data, user_id=current_user.id)

    for holding_data in holdings_data:
        db_strategy.holdings.append(StrategyHolding(**holding_data.model_dump()))

    db.add(db_strategy)
    db.commit()
    db.refresh(db_strategy)
    return db_strategy

@router.get("/", response_model=List[schemas.Strategy])
def read_strategies(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    strategies = (
        db.query(Strategy)
        .filter(Strategy.user_id == current_user.id)
        .offset(skip)
        .limit(limit)
        .all()
    )
    return strategies

@router.get("/{strategy_id}", response_model=schemas.Strategy)
def read_strategy(
    strategy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if db_strategy is None or db_strategy.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")
    return db_strategy

@router.post("/{strategy_id}/rebalance")
def rebalance_strategy(
    strategy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db_strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if db_strategy is None or db_strategy.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Strategy not found")

    # Fetch current holdings for the user
    # This is a placeholder; you'll need to implement fetching the actual portfolio
    current_holdings = db.query(Holding).filter(Holding.account.has(user_id=1)).all()

    rebalancer = Rebalancer(current_holdings, db_strategy)
    trades = rebalancer.calculate_trades()

    executed_trades = []
    for trade in trades:
        # Note: The rebalancer currently returns trade 'value'. 
        # A more robust implementation would calculate quantity based on current market price.
        # For now, we'll simulate with a small, fixed quantity for buys, and sell the full value.
        if trade['action'] == 'buy':
            # Placeholder: buy a small fixed amount for demonstration
            quantity = 1 
        else: # sell
            # Placeholder: need to get current holding quantity to sell
            # This requires a more detailed portfolio state
            quantity = 1 # Sell a fixed amount for now

        # Simulate trade execution
        executed_trades.append({"symbol": trade['symbol'], "quantity": quantity, "action": trade['action'], "status": "simulated"})

    return {"proposed_trades": trades, "executed_trades": executed_trades}
