from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, Enum, Numeric
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func, expression
from datetime import datetime
import enum
import os
import sys
from typing import List, Dict, Any

# Declare Base early
from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()

# Use shared in-memory SQLite during tests to avoid file permission issues
if "pytest" in sys.modules or os.getenv("TESTING") == "1":
    DATABASE_URL = "sqlite+pysqlite:///file::memory:?cache=shared"
else:
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./portfolio.db")

ENGINE_ARGS: dict = {}
# Allow SQLite connections across threads (FastAPI tests spawn workers)
if DATABASE_URL.startswith("sqlite"):
    ENGINE_ARGS["connect_args"] = {"check_same_thread": False}

# Lazily create engine so we can inspect URL afterwards
engine = create_engine(DATABASE_URL, **ENGINE_ARGS)

# Ensure tables exist during tests
if "pytest" in sys.modules or os.getenv("TESTING") == "1":
    Base.metadata.create_all(bind=engine)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    name = Column(String, index=True)
    description = Column(Text, nullable=True)
    rebalance_threshold = Column(Numeric(5, 2), default=5.0)  # e.g., 5% drift

    owner = relationship('User', back_populates='strategies')
    holdings = relationship("StrategyHolding", back_populates="strategy", cascade="all, delete-orphan")


class StrategyHolding(Base):
    __tablename__ = "strategy_holdings"

    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"))
    symbol = Column(String, index=True)
    target_weight = Column(Numeric(5, 4))  # e.g., 0.6000 for 60%

    strategy = relationship("Strategy", back_populates="holdings")

class AccountType(enum.Enum):
    CHECKING = "checking"
    SAVINGS = "savings"
    INVESTMENT = "investment"
    CREDIT = "credit"
    LOAN = "loan"
    MORTGAGE = "mortgage"
    RETIREMENT = "retirement"

class TransactionType(enum.Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    TRANSFER = "transfer"
    PURCHASE = "purchase"
    SALE = "sale"
    DIVIDEND = "dividend"
    INTEREST = "interest"
    FEE = "fee"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    name = Column(String)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Plaid integration
    plaid_access_token = Column(String, nullable=True)
    plaid_item_id = Column(String(100), nullable=True)
    
    # Relationships
    strategies = relationship('Strategy', back_populates='owner')
    accounts = relationship("Account", back_populates="user")
    transactions = relationship("Transaction", back_populates="user")
    portfolios = relationship("Portfolio", back_populates="user")

class Custodian(Base):
    """Financial institution that holds accounts (e.g., Fidelity, Vanguard, etc.)"""
    __tablename__ = "custodians"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)  # Internal identifier (e.g., 'fidelity', 'vanguard')
    display_name = Column(String(200))  # User-friendly name
    logo_url = Column(String(500), nullable=True)
    website = Column(String(200), nullable=True)
    is_active = Column(Boolean, server_default=expression.true(), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    accounts = relationship("Account", back_populates="custodian")


class Portfolio(Base):
    """A collection of accounts for a user"""
    __tablename__ = "portfolios"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    is_primary = Column(Boolean, server_default=expression.false(), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="portfolios")
    accounts = relationship("Account", back_populates="portfolio")
    
    def get_total_value(self) -> float:
        """Calculate the total market value of all accounts in this portfolio"""
        return sum(account.current_balance for account in self.accounts if account.current_balance is not None)


class Account(Base):
    __tablename__ = "accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    custodian_id = Column(Integer, ForeignKey("custodians.id", ondelete="SET NULL"), nullable=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id", ondelete="SET NULL"), nullable=True)
    
    # Account identification
    external_id = Column(String(100), nullable=True)  # External ID from the custodian
    name = Column(String(200), nullable=False)
    official_name = Column(String(500), nullable=True)
    account_type = Column(Enum(AccountType, values_callable=lambda x: [e.value for e in x]), nullable=False)
    account_subtype = Column(String(100), nullable=True)
    mask = Column(String(20), nullable=True)  # Last 4 digits for display
    
    # Integration identifiers
    plaid_account_id = Column(String(100), nullable=True)
    plaid_access_token = Column(String(255), nullable=True)
    alpaca_account_id = Column(String(100), nullable=True)
    alpaca_access_token = Column(String(255), nullable=True)
    plaid_item_id = Column(String(100), nullable=True)
    
    # Balance information
    current_balance = Column(Numeric(15, 2), default=0.0)
    available_balance = Column(Numeric(15, 2), nullable=True)
    iso_currency_code = Column(String(3), default="USD")
    
    # Metadata
    is_manual = Column(Boolean, server_default=expression.false(), nullable=False)  # If true, balances are manually entered
    is_active = Column(Boolean, server_default=expression.true(), nullable=False)
    last_synced_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="accounts")
    custodian = relationship("Custodian", back_populates="accounts")
    portfolio = relationship("Portfolio", back_populates="accounts")
    holdings = relationship("Holding", back_populates="account", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="account", cascade="all, delete-orphan")
    
    @property
    def display_name(self) -> str:
        """Generate a display name for the account"""
        if self.custodian and self.custodian.display_name:
            return f"{self.custodian.display_name} - {self.name}"
        return self.name
    
    def get_holdings_by_asset_class(self) -> Dict[str, List[Any]]:
        """Group holdings by asset class"""
        holdings_by_class = {}
        for holding in self.holdings:
            asset_class = holding.security_type or "Other"
            if asset_class not in holdings_by_class:
                holdings_by_class[asset_class] = []
            holdings_by_class[asset_class].append(holding)
        return holdings_by_class

class Holding(Base):
    __tablename__ = "holdings"
    
    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    
    # Security information
    symbol = Column(String(50), index=True, nullable=False)
    name = Column(String(200), nullable=False)
    security_type = Column(String(50))  # equity, bond, etf, mutual_fund, cash, etc.
    cusip = Column(String(20), nullable=True)
    isin = Column(String(20), nullable=True)
    
    # Position details
    quantity = Column(Numeric(15, 6), nullable=False)  # Support fractional shares
    market_value = Column(Numeric(15, 2), nullable=False)  # Total value of the position
    cost_basis = Column(Numeric(15, 2), nullable=True)  # Total cost basis
    unit_price = Column(Numeric(12, 4), nullable=True)  # Current price per unit
    cost_basis_per_share = Column(Numeric(12, 4), nullable=True)  # Average cost per share
    
    # Performance metrics
    unrealized_pl = Column(Numeric(15, 2), nullable=True)  # Unrealized profit/loss in dollars
    unrealized_pl_pct = Column(Numeric(8, 4), nullable=True)  # Unrealized profit/loss as percentage
    
    # Metadata
    last_updated = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    
    # Relationships
    account = relationship("Account", back_populates="holdings")
    
    def update_from_market_data(self, price: float, as_of: datetime = None):
        """Update holding with latest market data"""
        if self.quantity == 0:
            return
            
        self.unit_price = price
        self.market_value = self.quantity * price
        
        if self.cost_basis is not None and self.cost_basis > 0:
            self.unrealized_pl = self.market_value - self.cost_basis
            self.unrealized_pl_pct = (self.unrealized_pl / self.cost_basis) * 100
            self.cost_basis_per_share = self.cost_basis / self.quantity
            
        if as_of:
            self.last_updated = as_of
            
    @property
    def weight_in_account(self) -> float:
        """Calculate this holding's weight as a percentage of the account's total value"""
        if not self.account or not self.account.current_balance or self.account.current_balance == 0:
            return 0.0
        return (self.market_value / self.account.current_balance) * 100

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    
    # Transaction identification
    external_id = Column(String(100), unique=True, index=True, nullable=True)  # ID from custodian
    transaction_type = Column(Enum(TransactionType), nullable=False)
    
    # Transaction details
    amount = Column(Numeric(15, 2), nullable=False)  # Positive for credits, negative for debits
    description = Column(String(500), nullable=False)
    merchant_name = Column(String(200), nullable=True)
    category = Column(String(100), nullable=True)
    subcategory = Column(String(100), nullable=True)
    date = Column(DateTime, nullable=False)  # Date the transaction occurred
    
    # Investment-specific fields
    symbol = Column(String(50), nullable=True)
    quantity = Column(Numeric(15, 6), nullable=True)  # For investment transactions
    unit_price = Column(Numeric(12, 4), nullable=True)  # Price per unit
    fee = Column(Numeric(10, 2), nullable=True)  # Transaction fee
    
    # Metadata
    is_pending = Column(Boolean, server_default=expression.false(), nullable=False)
    is_recurring = Column(Boolean, server_default=expression.false(), nullable=False)
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="transactions")
    account = relationship("Account", back_populates="transactions")

def get_db():
    # For in-memory SQLite, each new connection may need the schema
    if "pytest" in sys.modules or os.getenv("TESTING") == "1":
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)