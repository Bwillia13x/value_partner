"""Unified account management system for multi-custodian support"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from enum import Enum
import logging
from dataclasses import dataclass

from .database import User, Account, Holding, Transaction, AccountType
from .integrations.plaid_service import PlaidService
# # from .alpaca_service import AlpacaService # Removed for debugging # Removed for debugging
from .analytics import PortfolioAnalytics

logger = logging.getLogger(__name__)

class CustodianType(Enum):
    PLAID = "plaid"
    ALPACA = "alpaca"
    MANUAL = "manual"
    DIRECT = "direct"

class AccountStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SYNCING = "syncing"
    ERROR = "error"
    DISCONNECTED = "disconnected"

@dataclass
class AccountSummary:
    """Unified account summary across all custodians"""
    user_id: int
    total_accounts: int
    total_value: float
    total_cash: float
    total_investments: float
    custodians: Dict[str, int]  # Count by custodian
    last_sync: Optional[datetime]
    sync_status: str
    
@dataclass
class HoldingSummary:
    """Aggregated holding across multiple accounts"""
    symbol: str
    name: str
    total_quantity: float
    total_market_value: float
    weighted_avg_cost: float
    accounts: List[Dict[str, Any]]  # List of accounts holding this symbol
    allocation_percentage: float
    
@dataclass
class AccountConnection:
    """Account connection information"""
    custodian: CustodianType
    account_id: str
    status: AccountStatus
    last_sync: Optional[datetime]
    error_message: Optional[str]
    capabilities: List[str]  # e.g., ['read', 'trade', 'transfer']

class UnifiedAccountManager:
    """Unified account management across multiple custodians"""
    
    def __init__(self, db: Session):
        self.db = db
        self.analytics = PortfolioAnalytics(db)
        
        # Initialize custodian services
        self.plaid_service = PlaidService()
        # self.alpaca_service = AlpacaService() # Removed for debugging
        
    def get_account_summary(self, user_id: int) -> AccountSummary:
        """Get unified account summary for a user"""
        
        accounts = self.db.query(Account).filter(Account.user_id == user_id).all()
        
        total_value = 0.0
        total_cash = 0.0
        total_investments = 0.0
        custodians = {}
        last_sync = None
        
        for account in accounts:
            total_value += account.current_balance or 0.0
            
            # Categorize by account type
            if account.account_type in [AccountType.CHECKING, AccountType.SAVINGS]:
                total_cash += account.current_balance or 0.0
            else:
                total_investments += account.current_balance or 0.0
                
            # Count by custodian
            custodian = self._get_account_custodian(account)
            custodians[custodian] = custodians.get(custodian, 0) + 1
            
            # Track latest sync
            if account.updated_at and (not last_sync or account.updated_at > last_sync):
                last_sync = account.updated_at
                
        # Determine overall sync status
        sync_status = self._get_overall_sync_status(user_id)
        
        return AccountSummary(
            user_id=user_id,
            total_accounts=len(accounts),
            total_value=total_value,
            total_cash=total_cash,
            total_investments=total_investments,
            custodians=custodians,
            last_sync=last_sync,
            sync_status=sync_status
        )
        
    def get_aggregated_holdings(self, user_id: int) -> List[HoldingSummary]:
        """Get aggregated holdings across all accounts"""
        
        # Get all holdings for user
        holdings = self.db.query(Holding).join(Account).filter(
            Account.user_id == user_id
        ).all()
        
        # Aggregate by symbol
        symbol_aggregates = {}
        total_portfolio_value = 0.0
        
        for holding in holdings:
            symbol = holding.symbol
            market_value = holding.market_value or 0.0
            quantity = holding.quantity or 0.0
            
            total_portfolio_value += market_value
            
            if symbol not in symbol_aggregates:
                symbol_aggregates[symbol] = {
                    'name': holding.name or symbol,
                    'total_quantity': 0.0,
                    'total_market_value': 0.0,
                    'total_cost_basis': 0.0,
                    'accounts': []
                }
                
            aggregate = symbol_aggregates[symbol]
            aggregate['total_quantity'] += quantity
            aggregate['total_market_value'] += market_value
            aggregate['total_cost_basis'] += (holding.cost_basis or 0.0)
            
            # Track which accounts hold this symbol
            account_info = {
                'account_id': holding.account_id,
                'account_name': holding.account.name,
                'custodian': self._get_account_custodian(holding.account),
                'quantity': quantity,
                'market_value': market_value
            }
            aggregate['accounts'].append(account_info)
            
        # Convert to HoldingSummary objects
        holding_summaries = []
        
        for symbol, data in symbol_aggregates.items():
            weighted_avg_cost = (
                data['total_cost_basis'] / data['total_quantity']
                if data['total_quantity'] > 0 else 0.0
            )
            
            allocation_percentage = (
                data['total_market_value'] / total_portfolio_value * 100
                if total_portfolio_value > 0 else 0.0
            )
            
            summary = HoldingSummary(
                symbol=symbol,
                name=data['name'],
                total_quantity=data['total_quantity'],
                total_market_value=data['total_market_value'],
                weighted_avg_cost=weighted_avg_cost,
                accounts=data['accounts'],
                allocation_percentage=allocation_percentage
            )
            
            holding_summaries.append(summary)
            
        # Sort by market value descending
        holding_summaries.sort(key=lambda x: x.total_market_value, reverse=True)
        
        return holding_summaries
        
    def get_account_connections(self, user_id: int) -> List[AccountConnection]:
        """Get connection status for all user accounts"""
        
        connections = []
        user = self.db.query(User).filter(User.id == user_id).first()
        
        if not user:
            return connections
            
        # Check Plaid connection
        if user.plaid_access_token:
            plaid_status = self._check_plaid_connection_status(user.plaid_access_token)
            connections.append(AccountConnection(
                custodian=CustodianType.PLAID,
                account_id=user.plaid_item_id or "unknown",
                status=plaid_status['status'],
                last_sync=plaid_status['last_sync'],
                error_message=plaid_status.get('error'),
                capabilities=['read', 'account_info']
            ))
            
        # Check Alpaca connection
        alpaca_token = getattr(user, 'alpaca_access_token', None)
        if alpaca_token:
            alpaca_status = self._check_alpaca_connection_status(alpaca_token)
            connections.append(AccountConnection(
                custodian=CustodianType.ALPACA,
                account_id="alpaca_account",
                status=alpaca_status['status'],
                last_sync=alpaca_status['last_sync'],
                error_message=alpaca_status.get('error'),
                capabilities=['read', 'trade', 'account_info']
            ))
            
        return connections
        
    def sync_all_accounts(self, user_id: int) -> Dict[str, Any]:
        """Sync all accounts for a user across all custodians"""
        
        logger.info(f"Starting full account sync for user {user_id}")
        
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {"error": "User not found"}
            
        sync_results = {
            "user_id": user_id,
            "plaid_sync": None,
            "alpaca_sync": None,
            "total_accounts_synced": 0,
            "total_holdings_synced": 0,
            "errors": []
        }
        
        # Sync Plaid accounts
        if user.plaid_access_token:
            try:
                plaid_result = self.plaid_service.sync_accounts(
                    user.plaid_access_token, self.db, user_id
                )
                sync_results["plaid_sync"] = plaid_result
                sync_results["total_accounts_synced"] += plaid_result.get("accounts_synced", 0)
                sync_results["total_holdings_synced"] += plaid_result.get("holdings_synced", 0)
            except Exception as e:
                error_msg = f"Plaid sync failed: {str(e)}"
                sync_results["errors"].append(error_msg)
                logger.error(error_msg)
                
        # Alpaca sync removed for debugging
                
        # Update user's last sync time
        user.updated_at = datetime.utcnow()
        self.db.commit()
        
        logger.info(f"Account sync completed for user {user_id}")
        return sync_results
        
    def get_transaction_history(self, user_id: int, days: int = 30, 
                              custodian: Optional[CustodianType] = None) -> List[Dict[str, Any]]:
        """Get transaction history across all accounts"""
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        query = self.db.query(Transaction).join(Account).filter(
            Account.user_id == user_id,
            Transaction.date >= start_date
        )
        
        # Filter by custodian if specified
        if custodian:
            # This would need custodian info in the account or transaction table
            pass
            
        transactions = query.order_by(Transaction.date.desc()).all()
        
        transaction_list = []
        for txn in transactions:
            transaction_list.append({
                "id": txn.id,
                "date": txn.date,
                "account_name": txn.account.name,
                "custodian": self._get_account_custodian(txn.account),
                "description": txn.description,
                "amount": txn.amount,
                "transaction_type": txn.transaction_type.value,
                "symbol": txn.symbol,
                "quantity": txn.quantity
            })
            
        return transaction_list
        
    def get_portfolio_allocation_by_custodian(self, user_id: int) -> Dict[str, Any]:
        """Get portfolio allocation breakdown by custodian"""
        
        accounts = self.db.query(Account).filter(Account.user_id == user_id).all()
        
        custodian_allocation = {}
        total_value = 0.0
        
        for account in accounts:
            custodian = self._get_account_custodian(account)
            account_value = account.current_balance or 0.0
            
            if custodian not in custodian_allocation:
                custodian_allocation[custodian] = {
                    "value": 0.0,
                    "accounts": 0,
                    "account_types": set()
                }
                
            custodian_allocation[custodian]["value"] += account_value
            custodian_allocation[custodian]["accounts"] += 1
            custodian_allocation[custodian]["account_types"].add(account.account_type.value)
            
            total_value += account_value
            
        # Convert to percentages and finalize
        for custodian, data in custodian_allocation.items():
            data["percentage"] = (data["value"] / total_value * 100) if total_value > 0 else 0
            data["account_types"] = list(data["account_types"])
            
        return {
            "total_value": total_value,
            "custodians": custodian_allocation
        }
        
    def _get_account_custodian(self, account: Account) -> str:
        """Determine custodian type for an account"""
        
        if account.plaid_account_id:
            return "plaid"
        elif account.institution_name == "Alpaca Markets":
            return "alpaca"
        elif account.institution_name:
            return account.institution_name.lower()
        else:
            return "manual"
            
    def _get_overall_sync_status(self, user_id: int) -> str:
        """Get overall sync status for user accounts"""
        
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return "error"
            
        # Check if any accounts haven't been synced recently
        recent_sync_threshold = datetime.utcnow() - timedelta(hours=24)
        
        accounts = self.db.query(Account).filter(Account.user_id == user_id).all()
        if not accounts:
            return "no_accounts"
            
        outdated_accounts = [
            acc for acc in accounts 
            if not acc.updated_at or acc.updated_at < recent_sync_threshold
        ]
        
        if len(outdated_accounts) == len(accounts):
            return "outdated"
        elif outdated_accounts:
            return "partial"
        else:
            return "current"
            
    def _check_plaid_connection_status(self, access_token: str) -> Dict[str, Any]:
        """Check Plaid connection status"""
        try:
            # This would check Plaid API for connection health
            return {
                "status": AccountStatus.ACTIVE,
                "last_sync": datetime.utcnow(),
                "error": None
            }
        except Exception as e:
            return {
                "status": AccountStatus.ERROR,
                "last_sync": None,
                "error": str(e)
            }
            
    
            
    def disconnect_custodian(self, user_id: int, custodian: CustodianType) -> bool:
        """Disconnect a custodian for a user"""
        try:
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user:
                return False
                
            if custodian == CustodianType.PLAID:
                user.plaid_access_token = None
                user.plaid_item_id = None
                
                # Optionally delete Plaid accounts
                self.db.query(Account).filter(
                    Account.user_id == user_id,
                    Account.plaid_account_id.isnot(None)
                ).delete()
                
            elif custodian == CustodianType.ALPACA:
                if hasattr(user, 'alpaca_access_token'):
                    user.alpaca_access_token = None
                    
                # Optionally delete Alpaca accounts
                self.db.query(Account).filter(
                    Account.user_id == user_id,
                    Account.institution_name == "Alpaca Markets"
                ).delete()
                
            self.db.commit()
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to disconnect {custodian} for user {user_id}: {e}")
            return False