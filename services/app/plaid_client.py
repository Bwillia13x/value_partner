from plaid.api import plaid_api
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.investments_holdings_get_request import InvestmentsHoldingsGetRequest
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.country_code import CountryCode
from plaid.model.products import Products
import plaid
from plaid.configuration import Configuration
from plaid.api_client import ApiClient
from datetime import datetime, timedelta
import os
from typing import List, Dict, Any

class PlaidClient:
    def __init__(self):
        self.client_id = os.getenv("PLAID_CLIENT_ID")
        self.secret = os.getenv("PLAID_SECRET")
        self.environment = os.getenv("PLAID_ENV", "sandbox")
        
        if not self.client_id or not self.secret:
            # Allow initialization without credentials for testing
            if not os.getenv("TESTING"):
                raise ValueError("PLAID_CLIENT_ID and PLAID_SECRET must be set")
            else:
                self.client_id = "test_client_id"
                self.secret = "test_secret"
        
        # Configure Plaid client
        host = plaid.Environment.Sandbox
        if self.environment == 'development':
            host = plaid.Environment.Development
        if self.environment == 'production':
            host = plaid.Environment.Production

        configuration = Configuration(
            host=host,
            api_key={
                'clientId': self.client_id,
                'secret': self.secret
            }
        )
        api_client = ApiClient(configuration)
        self.client = plaid_api.PlaidApi(api_client)
    
    def create_link_token(self, user_id: str, user_name: str) -> Dict[str, Any]:
        """Create a link token for Plaid Link initialization"""
        request = LinkTokenCreateRequest(
            products=[Products('transactions'), Products('investments')],
            client_name="Value Partner",
            country_codes=[CountryCode('US')],
            language='en',
            user=LinkTokenCreateRequestUser(
                client_user_id=str(user_id)
            )
        )
        
        response = self.client.link_token_create(request)
        return response.to_dict()
    
    def exchange_public_token(self, public_token: str) -> Dict[str, Any]:
        """Exchange public token for access token"""
        request = ItemPublicTokenExchangeRequest(
            public_token=public_token
        )
        
        response = self.client.item_public_token_exchange(request)
        return response.to_dict()
    
    def get_accounts(self, access_token: str) -> List[Dict[str, Any]]:
        """Get all accounts for a user"""
        request = AccountsGetRequest(access_token=access_token)
        response = self.client.accounts_get(request)
        return [account.to_dict() for account in response['accounts']]
    
    def get_transactions(self, access_token: str, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Get transactions for a date range"""
        request = TransactionsGetRequest(
            access_token=access_token,
            start_date=start_date.date(),
            end_date=end_date.date()
        )
        
        response = self.client.transactions_get(request)
        return [transaction.to_dict() for transaction in response['transactions']]
    
    def get_holdings(self, access_token: str) -> List[Dict[str, Any]]:
        """Get investment holdings"""
        request = InvestmentsHoldingsGetRequest(access_token=access_token)
        response = self.client.investments_holdings_get(request)
        return [holding.to_dict() for holding in response['holdings']]
    
    def get_recent_transactions(self, access_token: str, days: int = 30) -> List[Dict[str, Any]]:
        """Get recent transactions"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        return self.get_transactions(access_token, start_date, end_date)

# Global instance
plaid_client = PlaidClient()