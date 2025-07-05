from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import logging

from .database import get_db, User, Account, Holding, Transaction, AccountType
from .plaid_client import plaid_client
from .error_handling import error_handler, ErrorCategory, ErrorSeverity, ErrorContext

router = APIRouter(prefix="/portfolio", tags=["Portfolio"])

# Pydantic models
class LinkTokenResponse(BaseModel):
    link_token: str
    expiration: str

class ExchangeTokenRequest(BaseModel):
    public_token: str
    user_id: int

class AccountResponse(BaseModel):
    id: int
    name: str
    account_type: str
    current_balance: float
    available_balance: Optional[float]
    institution_name: Optional[str]
    mask: Optional[str]
    
    class Config:
        from_attributes = True

class HoldingResponse(BaseModel):
    id: int
    symbol: str
    name: str
    quantity: float
    market_value: float
    unit_price: Optional[float]
    
    class Config:
        from_attributes = True

class TransactionResponse(BaseModel):
    id: int
    amount: float
    description: str
    date: datetime
    category: Optional[str]
    merchant_name: Optional[str]
    
    class Config:
        from_attributes = True

class PortfolioSummary(BaseModel):
    total_value: float
    total_cash: float
    total_investments: float
    accounts_count: int
    holdings_count: int

@router.post("/link/token", response_model=LinkTokenResponse)
async def create_link_token(request: Request, user_id: int, db: Session = Depends(get_db)):
    """Create a Plaid Link token for account linking"""
    context = ErrorContext(
        user_id=user_id,
        function_name="create_link_token",
        request_id=getattr(request.state, 'request_id', None)
    )
    
    try:
        # Get or create user
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            user = User(id=user_id, email=f"user{user_id}@example.com", name=f"User {user_id}")
            db.add(user)
            db.commit()
        
        response = plaid_client.create_link_token(user_id, user.name or f"User {user_id}")
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
            "user_id": user_id,
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
    req: Request,
    exchange_request: ExchangeTokenRequest, 
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Exchange public token for access token and sync data"""
    context = ErrorContext(
        user_id=exchange_request.user_id,
        function_name="exchange_public_token",
        request_id=getattr(req.state, 'request_id', None)
    )
    
    try:
        # Exchange tokens
        response = plaid_client.exchange_public_token(exchange_request.public_token)
        access_token = response['access_token']
        item_id = response['item_id']
        
        # Update user with Plaid credentials
        user = db.query(User).filter(User.id == exchange_request.user_id).first()
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
        
        # Sync data in background
        background_tasks.add_task(sync_user_data, request.user_id, access_token, db)
        
        return {"message": "Account linked successfully", "syncing": True}
        
    except Exception as e:
        logging.error(f"Error exchanging token: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to link account")

@router.get("/accounts", response_model=List[AccountResponse])
async def get_accounts(user_id: int, db: Session = Depends(get_db)):
    """Get all accounts for a user"""
    accounts = db.query(Account).filter(Account.user_id == user_id, Account.is_active == True).all()
    return accounts

@router.get("/holdings", response_model=List[HoldingResponse])
async def get_holdings(user_id: int, account_id: Optional[int] = None, db: Session = Depends(get_db)):
    """Get holdings for a user or specific account"""
    query = db.query(Holding).join(Account).filter(Account.user_id == user_id)
    
    if account_id:
        query = query.filter(Holding.account_id == account_id)
    
    holdings = query.all()
    return holdings

@router.get("/transactions", response_model=List[TransactionResponse])
async def get_transactions(
    user_id: int, 
    account_id: Optional[int] = None,
    days: int = 30,
    db: Session = Depends(get_db)
):
    """Get recent transactions for a user"""
    start_date = datetime.now() - timedelta(days=days)
    
    query = db.query(Transaction).filter(
        Transaction.user_id == user_id,
        Transaction.date >= start_date
    )
    
    if account_id:
        query = query.filter(Transaction.account_id == account_id)
    
    transactions = query.order_by(Transaction.date.desc()).all()
    return transactions

@router.get("/summary", response_model=PortfolioSummary)
async def get_portfolio_summary(user_id: int, db: Session = Depends(get_db)):
    """Get portfolio summary for a user"""
    # Get all accounts
    accounts = db.query(Account).filter(Account.user_id == user_id, Account.is_active == True).all()
    
    total_cash = sum(acc.current_balance for acc in accounts if acc.account_type in [AccountType.CHECKING, AccountType.SAVINGS])
    total_investments = sum(acc.current_balance for acc in accounts if acc.account_type in [AccountType.INVESTMENT, AccountType.RETIREMENT])
    
    holdings_count = db.query(Holding).join(Account).filter(Account.user_id == user_id).count()
    
    return PortfolioSummary(
        total_value=total_cash + total_investments,
        total_cash=total_cash,
        total_investments=total_investments,
        accounts_count=len(accounts),
        holdings_count=holdings_count
    )

@router.post("/sync")
async def sync_portfolio(user_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Manually trigger portfolio sync"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.plaid_access_token:
        raise HTTPException(status_code=404, detail="User not found or not linked")
    
    background_tasks.add_task(sync_user_data, user_id, user.plaid_access_token, db)
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