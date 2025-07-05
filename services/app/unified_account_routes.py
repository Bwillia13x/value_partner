"""FastAPI routes for unified account management"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime

from .database import get_db
from .unified_accounts import (
    UnifiedAccountManager,
    CustodianType
)

router = APIRouter(prefix="/unified-accounts", tags=["unified-accounts"])

class AccountSummaryResponse(BaseModel):
    """Account summary response model"""
    user_id: int
    total_accounts: int
    total_value: float
    total_cash: float
    total_investments: float
    custodians: Dict[str, int]
    last_sync: Optional[datetime] = None
    sync_status: str

class HoldingSummaryResponse(BaseModel):
    """Holding summary response model"""
    symbol: str
    name: str
    total_quantity: float
    total_market_value: float
    weighted_avg_cost: float
    accounts: List[Dict[str, Any]]
    allocation_percentage: float

class AccountConnectionResponse(BaseModel):
    """Account connection response model"""
    custodian: str
    account_id: str
    status: str
    last_sync: Optional[datetime] = None
    error_message: Optional[str] = None
    capabilities: List[str]

class DisconnectRequest(BaseModel):
    """Disconnect custodian request model"""
    custodian: str
    confirm: bool = False

@router.get("/summary/{user_id}", response_model=AccountSummaryResponse)
async def get_user_account_summary(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Get unified account summary for a user"""
    try:
        manager = UnifiedAccountManager(db)
        summary = manager.get_account_summary(user_id)
        
        return AccountSummaryResponse(
            user_id=summary.user_id,
            total_accounts=summary.total_accounts,
            total_value=summary.total_value,
            total_cash=summary.total_cash,
            total_investments=summary.total_investments,
            custodians=summary.custodians,
            last_sync=summary.last_sync,
            sync_status=summary.sync_status
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/holdings/{user_id}", response_model=List[HoldingSummaryResponse])
async def get_aggregated_holdings(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Get aggregated holdings across all accounts"""
    try:
        manager = UnifiedAccountManager(db)
        holdings = manager.get_aggregated_holdings(user_id)
        
        return [
            HoldingSummaryResponse(
                symbol=holding.symbol,
                name=holding.name,
                total_quantity=holding.total_quantity,
                total_market_value=holding.total_market_value,
                weighted_avg_cost=holding.weighted_avg_cost,
                accounts=holding.accounts,
                allocation_percentage=holding.allocation_percentage
            )
            for holding in holdings
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/connections/{user_id}", response_model=List[AccountConnectionResponse])
async def get_account_connections(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Get connection status for all user accounts"""
    try:
        manager = UnifiedAccountManager(db)
        connections = manager.get_account_connections(user_id)
        
        return [
            AccountConnectionResponse(
                custodian=conn.custodian.value,
                account_id=conn.account_id,
                status=conn.status.value,
                last_sync=conn.last_sync,
                error_message=conn.error_message,
                capabilities=conn.capabilities
            )
            for conn in connections
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/sync/{user_id}")
async def sync_user_accounts(
    user_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Sync all accounts for a user across all custodians"""
    try:
        manager = UnifiedAccountManager(db)
        
        # For immediate sync, run in foreground
        # For better performance, you could queue this as a background task
        result = manager.sync_all_accounts(user_id)
        
        return {
            "message": f"Account sync completed for user {user_id}",
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/transactions/{user_id}")
async def get_transaction_history(
    user_id: int,
    days: int = 30,
    custodian: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get transaction history across all accounts"""
    try:
        manager = UnifiedAccountManager(db)
        
        custodian_enum = None
        if custodian:
            try:
                custodian_enum = CustodianType(custodian.lower())
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid custodian type")
                
        transactions = manager.get_transaction_history(user_id, days, custodian_enum)
        
        return {
            "user_id": user_id,
            "period_days": days,
            "custodian_filter": custodian,
            "transaction_count": len(transactions),
            "transactions": transactions
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/allocation/{user_id}")
async def get_portfolio_allocation_by_custodian(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Get portfolio allocation breakdown by custodian"""
    try:
        manager = UnifiedAccountManager(db)
        allocation = manager.get_portfolio_allocation_by_custodian(user_id)
        
        return {
            "user_id": user_id,
            "total_value": allocation["total_value"],
            "custodian_breakdown": allocation["custodians"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/disconnect/{user_id}")
async def disconnect_custodian(
    user_id: int,
    request: DisconnectRequest,
    db: Session = Depends(get_db)
):
    """Disconnect a custodian for a user"""
    if not request.confirm:
        raise HTTPException(
            status_code=400, 
            detail="Confirmation required. Set 'confirm' to true to proceed."
        )
        
    try:
        custodian_enum = CustodianType(request.custodian.lower())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid custodian type")
        
    try:
        manager = UnifiedAccountManager(db)
        success = manager.disconnect_custodian(user_id, custodian_enum)
        
        if success:
            return {
                "message": f"Successfully disconnected {request.custodian} for user {user_id}",
                "custodian": request.custodian,
                "user_id": user_id
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to disconnect custodian")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/reconciliation/{user_id}")
async def get_reconciliation_status(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Get reconciliation status for user accounts"""
    try:
        manager = UnifiedAccountManager(db)
        summary = manager.get_account_summary(user_id)
        
        return {
            "user_id": user_id,
            "sync_status": summary.sync_status,
            "last_sync": summary.last_sync,
            "total_accounts": summary.total_accounts,
            "recommendations": [
                "Schedule regular syncs to keep data current" if summary.sync_status == "outdated" else None,
                "Check connection status for failing accounts" if summary.sync_status == "error" else None,
                "Consider connecting additional accounts for complete portfolio view" if summary.total_accounts < 2 else None
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/custodians")
async def get_supported_custodians():
    """Get list of supported custodians"""
    return {
        "supported_custodians": [
            {
                "name": "Plaid",
                "type": "plaid",
                "description": "Connect to 10,000+ banks and brokerages",
                "capabilities": ["read", "account_info", "transactions"],
                "supported_account_types": ["checking", "savings", "investment", "credit"]
            },
            {
                "name": "Alpaca",
                "type": "alpaca",
                "description": "Commission-free stock trading",
                "capabilities": ["read", "trade", "account_info", "positions"],
                "supported_account_types": ["investment"]
            },
            {
                "name": "Manual Entry",
                "type": "manual",
                "description": "Manually enter account information",
                "capabilities": ["read"],
                "supported_account_types": ["all"]
            }
        ]
    }

@router.get("/stats/{user_id}")
async def get_account_statistics(
    user_id: int,
    db: Session = Depends(get_db)
):
    """Get account statistics and insights"""
    try:
        manager = UnifiedAccountManager(db)
        summary = manager.get_account_summary(user_id)
        holdings = manager.get_aggregated_holdings(user_id)
        allocation = manager.get_portfolio_allocation_by_custodian(user_id)
        
        # Calculate additional statistics
        total_positions = len(holdings)
        largest_position = max(holdings, key=lambda x: x.total_market_value) if holdings else None
        
        concentration_risk = "low"
        if largest_position and largest_position.allocation_percentage > 25:
            concentration_risk = "high"
        elif largest_position and largest_position.allocation_percentage > 15:
            concentration_risk = "medium"
            
        return {
            "user_id": user_id,
            "portfolio_statistics": {
                "total_value": summary.total_value,
                "cash_percentage": (summary.total_cash / summary.total_value * 100) if summary.total_value > 0 else 0,
                "investment_percentage": (summary.total_investments / summary.total_value * 100) if summary.total_value > 0 else 0,
                "total_positions": total_positions,
                "largest_position": {
                    "symbol": largest_position.symbol if largest_position else None,
                    "percentage": largest_position.allocation_percentage if largest_position else 0
                },
                "concentration_risk": concentration_risk,
                "custodian_count": len(summary.custodians),
                "account_count": summary.total_accounts
            },
            "custodian_breakdown": allocation["custodians"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))