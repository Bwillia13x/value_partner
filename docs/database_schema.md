# Database Schema Documentation

## 1. Introduction

This document outlines the database schema for the Value Investing Platform, managed via SQLAlchemy ORM. The primary models are defined in `services/app/database.py`.

## 2. Core Models

### 2.1. `User`

-   **Purpose:** Represents an end-user of the platform.
-   **Key Fields:**
    -   `id` (Integer, Primary Key): Unique identifier for the user.
    -   `username` (String, Unique, Indexed, Nullable): User's chosen username (can be null if email is primary identifier).
    -   `email` (String, Unique, Indexed, Not Nullable): User's email address.
    -   `hashed_password` (String, Not Nullable): Hashed password for authentication.
    -   `name` (String): User's full name.
    -   `plaid_access_token` (String, Nullable): Plaid access token for linking financial accounts.
    -   `plaid_item_id` (String, Nullable): Plaid item ID.
    -   `created_at` (DateTime): Timestamp of user creation.
    -   `updated_at` (DateTime): Timestamp of last update.
-   **Relationships:**
    -   `strategies` (One-to-Many with `Strategy`): Strategies created by the user. Back-populates `Strategy.owner`.
    -   `accounts` (One-to-Many with `Account`): Financial accounts linked by the user. Back-populates `Account.user`.
    -   `transactions` (One-to-Many with `Transaction`): Transactions associated with the user's accounts. Back-populates `Transaction.user`.
    -   `portfolios` (One-to-Many with `Portfolio`): Portfolios created by the user. Back-populates `Portfolio.user`.

### 2.2. `Custodian`

-   **Purpose:** Represents a financial institution that holds accounts (e.g., Fidelity, Vanguard).
-   **Key Fields:**
    -   `id` (Integer, Primary Key): Unique identifier for the custodian.
    -   `name` (String, Unique, Not Nullable): Internal identifier (e.g., 'fidelity').
    -   `display_name` (String): User-friendly name (e.g., "Fidelity Investments").
    -   `logo_url` (String, Nullable): URL to the custodian's logo.
    -   `website` (String, Nullable): Custodian's website URL.
    -   `is_active` (Boolean, Default: True): Whether the custodian integration is active.
-   **Relationships:**
    -   `accounts` (One-to-Many with `Account`): Accounts held at this custodian. Back-populates `Account.custodian`.

### 2.3. `Portfolio`

-   **Purpose:** A user-defined collection of financial accounts.
-   **Key Fields:**
    -   `id` (Integer, Primary Key): Unique identifier for the portfolio.
    -   `user_id` (Integer, Foreign Key to `User.id`, Not Nullable, Cascade Delete): Owning user.
    -   `name` (String, Not Nullable): Name of the portfolio.
    -   `description` (Text, Nullable): Optional description.
    -   `is_primary` (Boolean, Default: False): Whether this is the user's primary portfolio.
-   **Relationships:**
    -   `user` (Many-to-One with `User`): The user who owns this portfolio. Back-populates `User.portfolios`.
    -   `accounts` (One-to-Many with `Account`): Accounts included in this portfolio. Back-populates `Account.portfolio`.
-   **Instance Methods:**
    -   `get_total_value()`: Calculates the total market value of all accounts in this portfolio.

### 2.4. `Account`

-   **Purpose:** Represents a specific financial account (e.g., checking, savings, brokerage).
-   **Key Fields:**
    -   `id` (Integer, Primary Key): Unique identifier for the account.
    -   `user_id` (Integer, Foreign Key to `User.id`, Not Nullable, Cascade Delete): Owning user.
    -   `custodian_id` (Integer, Foreign Key to `Custodian.id`, Nullable, Set Null on Delete): Associated custodian.
    -   `portfolio_id` (Integer, Foreign Key to `Portfolio.id`, Nullable, Set Null on Delete): Portfolio this account belongs to.
    -   `external_id` (String, Nullable): External ID from the custodian (e.g., Plaid account ID).
    -   `name` (String, Not Nullable): Name of the account (e.g., "Chase Checking").
    -   `official_name` (String, Nullable): Official name from the institution.
    -   `account_type` (Enum `AccountType`, Not Nullable): Type of account (e.g., `checking`, `investment`).
    -   `account_subtype` (String, Nullable): Subtype (e.g., `401k`, `roth`).
    -   `mask` (String, Nullable): Last 4 digits for display.
    -   `plaid_account_id`, `plaid_access_token`, `plaid_item_id` (Strings, Nullable): Plaid specific identifiers.
    -   `alpaca_account_id`, `alpaca_access_token` (Strings, Nullable): Alpaca specific identifiers.
    -   `current_balance` (Numeric, Default: 0.0): Current balance of the account.
    -   `available_balance` (Numeric, Nullable): Available balance.
    -   `iso_currency_code` (String, Default: "USD"): Currency code.
    -   `is_manual` (Boolean, Default: False): If true, balances are manually entered.
    -   `is_active` (Boolean, Default: True): Whether the account is active.
    -   `last_synced_at` (DateTime, Nullable): Timestamp of the last data sync.
-   **Relationships:**
    -   `user` (Many-to-One with `User`): Owning user. Back-populates `User.accounts`.
    -   `custodian` (Many-to-One with `Custodian`): Custodian of the account. Back-populates `Custodian.accounts`.
    -   `portfolio` (Many-to-One with `Portfolio`): Portfolio this account belongs to. Back-populates `Portfolio.accounts`.
    -   `holdings` (One-to-Many with `Holding`): Investment holdings in this account. Cascade delete. Back-populates `Holding.account`.
    -   `transactions` (One-to-Many with `Transaction`): Transactions in this account. Cascade delete. Back-populates `Transaction.account`.
-   **Properties/Methods:**
    -   `display_name`: Generates a display name (e.g., "Fidelity - Brokerage Account").
    -   `get_holdings_by_asset_class()`: Groups holdings by asset class.

### 2.5. `Holding`

-   **Purpose:** Represents a specific investment holding (e.g., shares of a stock, ETF).
-   **Key Fields:**
    -   `id` (Integer, Primary Key): Unique identifier.
    -   `account_id` (Integer, Foreign Key to `Account.id`, Not Nullable, Cascade Delete): Account this holding belongs to.
    -   `symbol` (String, Indexed, Not Nullable): Ticker symbol (e.g., "AAPL").
    -   `name` (String, Not Nullable): Name of the security (e.g., "Apple Inc.").
    -   `security_type` (String): Type of security (e.g., `equity`, `etf`, `mutual_fund`).
    -   `cusip`, `isin` (Strings, Nullable): Other security identifiers.
    -   `quantity` (Numeric, Not Nullable): Number of shares/units held.
    -   `market_value` (Numeric, Not Nullable): Total current market value of the position.
    -   `cost_basis` (Numeric, Nullable): Total cost basis for the position.
    -   `unit_price` (Numeric, Nullable): Current price per share/unit.
    -   `cost_basis_per_share` (Numeric, Nullable): Average cost per share.
    -   `unrealized_pl`, `unrealized_pl_pct` (Numeric, Nullable): Unrealized profit/loss.
    -   `last_updated` (DateTime): When this holding's data was last updated.
-   **Relationships:**
    -   `account` (Many-to-One with `Account`): The account holding this security. Back-populates `Account.holdings`.
-   **Instance Methods:**
    -   `update_from_market_data(price, as_of)`: Updates market value, P/L based on new price.
-   **Properties:**
    -   `weight_in_account`: Calculates this holding's weight in the account.

### 2.6. `Transaction`

-   **Purpose:** Represents a financial transaction (deposit, withdrawal, buy, sell, dividend, etc.).
-   **Key Fields:**
    -   `id` (Integer, Primary Key): Unique identifier.
    -   `user_id` (Integer, Foreign Key to `User.id`, Not Nullable, Cascade Delete): User associated with the transaction.
    -   `account_id` (Integer, Foreign Key to `Account.id`, Not Nullable, Cascade Delete): Account this transaction belongs to.
    -   `external_id` (String, Unique, Indexed, Nullable): ID from the custodian/Plaid.
    -   `transaction_type` (Enum `TransactionType`, Not Nullable): Type of transaction (e.g., `deposit`, `purchase`).
    -   `amount` (Numeric, Not Nullable): Transaction amount (positive for credits, negative for debits).
    -   `description` (String, Not Nullable): Description of the transaction.
    -   `merchant_name` (String, Nullable): Merchant name, if applicable.
    -   `category`, `subcategory` (Strings, Nullable): Transaction categories.
    -   `date` (DateTime, Not Nullable): Date the transaction occurred.
    -   `symbol` (String, Nullable): Ticker symbol, for investment transactions.
    -   `quantity` (Numeric, Nullable): Number of shares/units, for investment transactions.
    -   `unit_price` (Numeric, Nullable): Price per share/unit.
    -   `fee` (Numeric, Nullable): Transaction fee.
    -   `is_pending` (Boolean, Default: False): Whether the transaction is pending.
    -   `is_recurring` (Boolean, Default: False): Whether this is a recurring transaction.
    -   `notes` (Text, Nullable): User notes.
-   **Relationships:**
    -   `user` (Many-to-One with `User`): User associated with the transaction. Back-populates `User.transactions`.
    -   `account` (Many-to-One with `Account`): Account for this transaction. Back-populates `Account.transactions`.

### 2.7. `Strategy`

-   **Purpose:** Represents a user-defined investment strategy or model portfolio.
-   **Key Fields:**
    -   `id` (Integer, Primary Key): Unique identifier.
    -   `user_id` (Integer, Foreign Key to `User.id`, Not Nullable): Owning user.
    -   `name` (String, Indexed): Name of the strategy.
    -   `description` (Text, Nullable): Description.
    -   `rebalance_threshold` (Numeric, Default: 5.0): Rebalancing threshold (e.g., 5% drift).
-   **Relationships:**
    -   `owner` (Many-to-One with `User`): The user who owns this strategy. Back-populates `User.strategies`.
    -   `holdings` (One-to-Many with `StrategyHolding`): Target holdings for this strategy. Cascade delete. Back-populates `StrategyHolding.strategy`.

### 2.8. `StrategyHolding`

-   **Purpose:** Defines a target holding (symbol and weight) within an investment strategy.
-   **Key Fields:**
    -   `id` (Integer, Primary Key): Unique identifier.
    -   `strategy_id` (Integer, Foreign Key to `Strategy.id`): Strategy this holding belongs to.
    -   `symbol` (String, Indexed): Ticker symbol of the target asset.
    -   `target_weight` (Numeric): Target weight for this asset in the strategy (e.g., 0.60 for 60%).
-   **Relationships:**
    -   `strategy` (Many-to-One with `Strategy`): The strategy this holding definition belongs to. Back-populates `Strategy.holdings`.

## 3. Enums

-   **`AccountType`**: Defines valid types for accounts (e.g., `CHECKING`, `SAVINGS`, `INVESTMENT`).
-   **`TransactionType`**: Defines valid types for transactions (e.g., `DEPOSIT`, `WITHDRAWAL`, `PURCHASE`, `SALE`).

---

This documentation provides a high-level overview. For exact column types, constraints, and default values, refer to the SQLAlchemy model definitions in `services/app/database.py`.
