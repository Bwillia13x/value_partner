"""Plaid integration service for account aggregation"""
import os
from typing import Dict, List
from datetime import datetime
import plaid
from plaid.api import plaid_api
from plaid.model.products import Products
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.accounts_balance_get_request import AccountsBalanceGetRequest
from plaid.model.investments_holdings_get_request import InvestmentsHoldingsGetRequest
from sqlalchemy.orm import Session
from ..database import Account, Holding
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PlaidService:
    """Service for handling Plaid API interactions"""
    
    def __init__(self, client_id: str = None, secret: str = None, env: str = 'sandbox'):
        """Initialize Plaid client with credentials"""
        self.client_id = client_id or os.getenv('PLAID_CLIENT_ID')
        self.secret = secret or os.getenv('PLAID_SECRET')
        self.env = env.lower()
        
        if not all([self.client_id, self.secret]):
            raise ValueError("Plaid client_id and secret must be provided or set in environment")
            
        configuration = plaid.Configuration(
            host=plaid.Environment.Sandbox if self.env == 'sandbox' else plaid.Environment.Development,
            api_key={
                'clientId': self.client_id,
                'secret': self.secret,
                'plaidVersion': '2020-09-14'
            }
        )
        
        api_client = plaid.ApiClient(configuration)
        self.client = plaid_api.PlaidApi(api_client)
    
    def create_link_token(self, user_id: str) -> Dict:
        """Generate a link token for the Plaid Link UI"""
        request = LinkTokenCreateRequest(
            user={"client_user_id": str(user_id)},
            client_name="Value Partner",
            products=[Products("investments"), Products("transactions")],
            country_codes=["US"],
            language="en",
            webhook=os.getenv('PLAID_WEBHOOK_URL', '')
        )
        
        try:
            response = self.client.link_token_create(request)
            return {"link_token": response.link_token, "expiration": response.expiration}
        except Exception as e:
            logger.error(f"Error creating link token: {e}")
            raise
    
    def exchange_public_token(self, public_token: str) -> Dict:
        """Exchange public token for access token and item ID"""
        request = ItemPublicTokenExchangeRequest(public_token=public_token)
        
        try:
            response = self.client.item_public_token_exchange(request)
            return {
                "access_token": response.access_token,
                "item_id": response.item_id
            }
        except Exception as e:
            logger.error(f"Error exchanging public token: {e}")
            raise
    
    def get_accounts(self, access_token: str) -> List[Dict]:
        """Retrieve account details from Plaid"""
        request = AccountsBalanceGetRequest(access_token=access_token)
        
        try:
            response = self.client.accounts_balance_get(request)
            return [{
                "account_id": account.account_id,
                "name": account.name,
                "official_name": account.official_name,
                "type": account.type,
                "subtype": account.subtype,
                "mask": account.mask,
                "balances": {
                    "available": account.balances.available,
                    "current": account.balances.current,
                    "iso_currency_code": account.balances.iso_currency_code,
                    "unofficial_currency_code": account.balances.unofficial_currency_code
                }
            } for account in response.accounts]
        except Exception as e:
            logger.error(f"Error fetching accounts: {e}")
            raise
    
    def get_investment_holdings(self, access_token: str) -> List[Dict]:
        """Retrieve investment holdings from Plaid"""
        request = InvestmentsHoldingsGetRequest(access_token=access_token)
        
        try:
            response = self.client.investments_holdings_get(request)
            
            holdings = []
            for holding in response.holdings:
                security = next((s for s in response.securities if s.security_id == holding.security_id), None)
                if not security:
                    continue
                    
                holdings.append({
                    "account_id": holding.account_id,
                    "security_id": holding.security_id,
                    "ticker_symbol": security.ticker_symbol,
                    "name": security.name,
                    "type": security.type,
                    "quantity": holding.quantity,
                    "cost_basis": holding.cost_basis,
                    "institution_price": holding.institution_price,
                    "institution_value": holding.institution_value,
                    "iso_currency_code": holding.iso_currency_code,
                    "unofficial_currency_code": holding.unofficial_currency_code
                })
                
            return holdings
            
        except Exception as e:
            logger.error(f"Error fetching investment holdings: {e}")
            raise
    
    def sync_plaid_data(self, user_id: str, access_token: str, item_id: str, db: Session) -> Dict:
        """Sync Plaid account data to our database"""
        try:
            # Get accounts and holdings
            accounts = self.get_accounts(access_token)
            holdings = self.get_investment_holdings(access_token)
            
            # Update or create accounts
            account_map = {}
            for acc in accounts:
                if acc['type'] != 'investment':
                    continue
                    
                account = db.query(Account).filter(
                    Account.plaid_account_id == acc['account_id'],
                    Account.user_id == user_id
                ).first()
                
                if not account:
                    account = Account(
                        user_id=user_id,
                        name=acc['name'],
                        account_type='investment',
                        plaid_account_id=acc['account_id'],
                        plaid_item_id=item_id,
                        institution_name=acc.get('institution_name', 'Unknown'),
                        current_balance=acc['balances']['current'],
                        currency=acc['balances']['iso_currency_code'] or 'USD',
                        is_active=True
                    )
                    db.add(account)
                    db.flush()
                
                account_map[acc['account_id']] = account.id
            
            # Update or create holdings
            for holding in holdings:
                if holding['account_id'] not in account_map:
                    continue
                    
                db_holding = db.query(Holding).filter(
                    Holding.account_id == account_map[holding['account_id']],
                    Holding.security_id == holding['security_id']
                ).first()
                
                if not db_holding:
                    db_holding = Holding(
                        account_id=account_map[holding['account_id']],
                        security_id=holding['security_id'],
                        ticker=holding['ticker_symbol'],
                        name=holding['name'],
                        security_type=holding['type'],
                        quantity=holding['quantity'],
                        cost_basis=holding['cost_basis'] or holding['institution_value'],
                        market_value=holding['institution_value'],
                        currency=holding['iso_currency_code'] or 'USD',
                        last_updated=datetime.utcnow()
                    )
                    db.add(db_holding)
                else:
                    db_holding.quantity = holding['quantity']
                    db_holding.market_value = holding['institution_value']
                    db_holding.last_updated = datetime.utcnow()
            
            db.commit()
            return {"status": "success", "accounts_updated": len(accounts), "holdings_updated": len(holdings)}
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error syncing Plaid data: {e}")
            raise


