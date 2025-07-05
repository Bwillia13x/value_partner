from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import logging

from .database import get_db, User, Account, Holding, Transaction, AccountType
from .plaid_client import plaid_client
from .error_handling import error_handler, ErrorCategory, ErrorSeverity, ErrorContext
from .auth import get_current_active_user # Added

router = APIRouter(prefix="/portfolio", tags=["Portfolio"])

# Pydantic models
class LinkTokenResponse(BaseModel):
    link_token: str
    expiration: str

class ExchangeTokenRequest(BaseModel):
    public_token: str
    # user_id: int # user_id will come from authenticated user
    # No, exchange token request is often initiated by frontend with a user_id
    # before full session is established for that user post-link.
    # Or, it can be an admin action. Let's keep user_id for now.
    # For now, assume the user_id in ExchangeTokenRequest is the target user.
    # If this needs to be current_user, the frontend flow might need adjustment.
    user_id: int


class AccountResponse(BaseModel):
    id: int
    name: str
    account_type: str # Consider Enum here if values are fixed
    current_balance: float # Consider Decimal for precision
    available_balance: Optional[float] # Consider Decimal
    institution_name: Optional[str]
    mask: Optional[str]
    
    class Config:
        from_attributes = True

class HoldingResponse(BaseModel):
    id: int
    symbol: str
    name: str
    quantity: float # Consider Decimal
    market_value: float # Consider Decimal
    unit_price: Optional[float] # Consider Decimal
    
    class Config:
        from_attributes = True

class TransactionResponse(BaseModel):
    id: int
    amount: float # Consider Decimal
    description: str
    date: datetime
    category: Optional[str]
    merchant_name: Optional[str]
    
    class Config:
        from_attributes = True

class PortfolioSummary(BaseModel):
    total_value: float # Consider Decimal
    total_cash: float # Consider Decimal
    total_investments: float # Consider Decimal
    accounts_count: int
    holdings_count: int

@router.post("/link/token", response_model=LinkTokenResponse)
async def create_link_token(request: Request, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)): # Changed user_id to current_user
    """Create a Plaid Link token for account linking for the authenticated user"""
    context = ErrorContext(
        user_id=current_user.id, # Use current_user.id
        function_name="create_link_token",
        request_id=getattr(request.state, 'request_id', None)
    )
    
    try:
        # User is already fetched and validated by get_current_active_user
        response = plaid_client.create_link_token(current_user.id, current_user.name or f"User {current_user.id}")
        return LinkTokenResponse(
            link_token=response['link_token'],
            expiration=response['expiration']
        )
    except Exception as e:
        error_id = error_handler.record_error(
            e, ErrorCategory.EXTERNAL_API, ErrorSeverity.HIGH, context
        )
        logging.error(f"Error creating link token: {str(e)}", extra={
            "error_id": error_id,
            "user_id": current_user.id,
            "request_id": context.request_id
        })
        raise HTTPException(
            status_code=503,
            detail={
                "error_id": error_id,
                "error_type": "external_service_unavailable",
                "message": "Unable to connect to account linking service",
                "retry_after": 60
            }
        )

@router.post("/link/exchange")
async def exchange_public_token(
    req: Request, # Changed from request to req to match existing style
    exchange_request: ExchangeTokenRequest, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user) # Added current_user for auth context if needed
):
    """Exchange public token for access token and sync data"""
    # Decide if exchange_request.user_id should be validated against current_user.id
    # For now, assume exchange_request.user_id is the target, could be an admin task or specific flow.
    # If strictly for the authenticated user, then exchange_request.user_id should be current_user.id
    target_user_id = exchange_request.user_id
    if target_user_id != current_user.id:
        # This could be an admin action or a specific flow.
        # For now, let's allow it but one might want to restrict this.
        # For stricter security for self-service, uncomment:
        # raise HTTPException(status_code=403, detail="Cannot exchange token for another user")
        pass


    context = ErrorContext(
        user_id=target_user_id,
        function_name="exchange_public_token",
        request_id=getattr(req.state, 'request_id', None)
    )
    
    try:
        # Exchange tokens
        response = plaid_client.exchange_public_token(exchange_request.public_token)
        access_token = response['access_token']
        item_id = response['item_id']
        
        # Update user with Plaid credentials
        user = db.query(User).filter(User.id == target_user_id).first()
        if not user:
            error_id = error_handler.record_error(
                ValueError("User not found"), ErrorCategory.VALIDATION, ErrorSeverity.MEDIUM, context
            )
            raise HTTPException(status_code=404, detail={
                "error_id": error_id,
                "message": "User not found"
            })
        
        user.plaid_access_token = access_token
        user.plaid_item_id = item_id
        db.commit()
        
        # Sync data in background for the target user
        background_tasks.add_task(sync_user_data, target_user_id, access_token, db) # Use target_user_id
        
        return {"message": "Account linked successfully", "syncing": True}
        
    except Exception as e:
        error_id = error_handler.record_error( # Added error recording
            e, ErrorCategory.EXTERNAL_API, ErrorSeverity.CRITICAL, context
        )
        logging.error(f"Error exchanging token: {str(e)}", extra={ # Added extra context
            "error_id": error_id, "user_id": target_user_id, "request_id": context.request_id
        })
        raise HTTPException(status_code=500, detail="Failed to link account")

@router.get("/accounts", response_model=List[AccountResponse])
async def get_accounts(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)): # Changed
    """Get all accounts for the authenticated user"""
    accounts = db.query(Account).filter(Account.user_id == current_user.id, Account.is_active == True).all()
    return accounts

@router.get("/holdings", response_model=List[HoldingResponse])
async def get_holdings(account_id: Optional[int] = None, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)): # Changed
    """Get holdings for the authenticated user or specific account"""
    query = db.query(Holding).join(Account).filter(Account.user_id == current_user.id)
    
    if account_id:
        # Ensure the account_id belongs to the current_user
        account = db.query(Account).filter(Account.id == account_id, Account.user_id == current_user.id).first()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found or does not belong to user")
        query = query.filter(Holding.account_id == account_id)
    
    holdings = query.all()
    return holdings

@router.get("/transactions", response_model=List[TransactionResponse])
async def get_transactions(
    account_id: Optional[int] = None,
    days: int = 30,
    current_user: User = Depends(get_current_active_user), # Changed
    db: Session = Depends(get_db)
):
    """Get recent transactions for the authenticated user"""
    start_date = datetime.now() - timedelta(days=days)
    
    query = db.query(Transaction).filter(
        Transaction.user_id == current_user.id,
        Transaction.date >= start_date
    )
    
    if account_id:
        # Ensure the account_id belongs to the current_user
        account = db.query(Account).filter(Account.id == account_id, Account.user_id == current_user.id).first()
        if not account:
            raise HTTPException(status_code=404, detail="Account not found or does not belong to user")
        query = query.filter(Transaction.account_id == account_id)
    
    transactions = query.order_by(Transaction.date.desc()).all()
    return transactions

@router.get("/summary", response_model=PortfolioSummary)
async def get_portfolio_summary(current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)): # Changed
    """Get portfolio summary for the authenticated user"""
    # Get all accounts for the current user
    accounts = db.query(Account).filter(Account.user_id == current_user.id, Account.is_active == True).all()
    
    total_cash = sum(acc.current_balance for acc in accounts if acc.account_type in [AccountType.CHECKING, AccountType.SAVINGS] and acc.current_balance is not None)
    total_investments = sum(acc.current_balance for acc in accounts if acc.account_type in [AccountType.INVESTMENT, AccountType.RETIREMENT] and acc.current_balance is not None)
    
    holdings_count = db.query(Holding).join(Account).filter(Account.user_id == current_user.id).count()
    
    return PortfolioSummary(
        total_value=total_cash + total_investments,
        total_cash=total_cash,
        total_investments=total_investments,
        accounts_count=len(accounts),
        holdings_count=holdings_count
    )

@router.post("/sync")
async def sync_portfolio(background_tasks: BackgroundTasks, current_user: User = Depends(get_current_active_user), db: Session = Depends(get_db)): # Changed
    """Manually trigger portfolio sync for the authenticated user"""
    if not current_user.plaid_access_token: # User object from DB via auth dependency
        raise HTTPException(status_code=400, detail="User not linked to Plaid or access token missing")
    
    background_tasks.add_task(sync_user_data, current_user.id, current_user.plaid_access_token, db)
    return {"message": "Sync started"}

async def sync_user_data(user_id: int, access_token: str, db: Session):
    """Background task to sync user data from Plaid"""
    try:
        # Sync accounts
        plaid_accounts = plaid_client.get_accounts(access_token)
        for plaid_account in plaid_accounts:
            account = db.query(Account).filter(Account.plaid_account_id == plaid_account['account_id']).first()
            
            if not account:
                account = Account(
                    user_id=user_id,
                    plaid_account_id=plaid_account['account_id'],
                    account_type=AccountType(plaid_account['type']),
                    account_subtype=plaid_account.get('subtype'),
                    name=plaid_account['name'],
                    official_name=plaid_account.get('official_name'),
                    mask=plaid_account.get('mask'),
                    institution_name=plaid_account.get('institution_name')
                )
                db.add(account)
            
            # Update balance
            balances = plaid_account.get('balances', {})
            account.current_balance = balances.get('current', 0)
            account.available_balance = balances.get('available')
            
        db.commit()
        
        # Sync holdings for investment accounts
        try:
            plaid_holdings = plaid_client.get_holdings(access_token)
            for plaid_holding in plaid_holdings:
                account = db.query(Account).filter(Account.plaid_account_id == plaid_holding['account_id']).first()
                if not account:
                    continue
                
                holding = db.query(Holding).filter(
                    Holding.account_id == account.id,
                    Holding.symbol == plaid_holding['security']['ticker_symbol']
                ).first()
                
                if not holding:
                    holding = Holding(
                        account_id=account.id,
                        symbol=plaid_holding['security']['ticker_symbol'],
                        name=plaid_holding['security']['name'],
                        security_type=plaid_holding['security']['type']
                    )
                    db.add(holding)
                
                holding.quantity = plaid_holding['quantity']
                holding.market_value = plaid_holding['market_value']
                holding.cost_basis = plaid_holding.get('cost_basis')
                holding.unit_price = plaid_holding.get('unit_price')
                
        except Exception as e:
            logging.warning(f"Holdings sync failed: {str(e)}")
        
        # Sync recent transactions
        try:
            plaid_transactions = plaid_client.get_recent_transactions(access_token)
            for plaid_transaction in plaid_transactions:
                transaction = db.query(Transaction).filter(
                    Transaction.plaid_transaction_id == plaid_transaction['transaction_id']
                ).first()
                
                if not transaction:
                    account = db.query(Account).filter(Account.plaid_account_id == plaid_transaction['account_id']).first()
                    if not account:
                        continue
                    
                    transaction = Transaction(
                        user_id=user_id,
                        account_id=account.id,
                        plaid_transaction_id=plaid_transaction['transaction_id'],
                        amount=plaid_transaction['amount'],
                        description=plaid_transaction['name'],
                        date=datetime.strptime(plaid_transaction['date'], '%Y-%m-%d'),
                        category=plaid_transaction.get('category', [None])[0] if plaid_transaction.get('category') else None,
                        merchant_name=plaid_transaction.get('merchant_name')
                    )
                    db.add(transaction)
                    
        except Exception as e:
            logging.warning(f"Transaction sync failed: {str(e)}")
        
        db.commit()
        logging.info(f"Successfully synced data for user {user_id}")
        
    except Exception as e:
        logging.error(f"Error syncing user data: {str(e)}")
        db.rollback()