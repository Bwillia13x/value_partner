"""Add critical database constraints

Revision ID: 583c6e86a6fd
Revises: dd2b332b3d0d
Create Date: 2025-07-04 09:47:27.889648

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '583c6e86a6fd'
down_revision: Union[str, None] = 'dd2b332b3d0d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add NOT NULL constraints for critical fields
    with op.batch_alter_table("strategies", schema=None) as batch_op:
        batch_op.alter_column('name', nullable=False)
        batch_op.create_check_constraint(
            "ck_strategies_rebalance_threshold_positive",
            "rebalance_threshold >= 0 AND rebalance_threshold <= 100"
        )
    
    with op.batch_alter_table("strategy_holdings", schema=None) as batch_op:
        batch_op.alter_column('symbol', nullable=False)
        batch_op.alter_column('strategy_id', nullable=False)
        batch_op.alter_column('target_weight', nullable=False)
        batch_op.create_check_constraint(
            "ck_strategy_holdings_target_weight_valid",
            "target_weight >= 0 AND target_weight <= 1"
        )
        batch_op.create_unique_constraint(
            "uq_strategy_holdings_strategy_symbol",
            ['strategy_id', 'symbol']
        )
    
    with op.batch_alter_table("custodians", schema=None) as batch_op:
        batch_op.alter_column('name', nullable=False)
        batch_op.alter_column('display_name', nullable=False)
    
    with op.batch_alter_table("portfolios", schema=None) as batch_op:
        batch_op.alter_column('name', nullable=False)
        batch_op.create_unique_constraint(
            "uq_portfolios_user_name",
            ['user_id', 'name']
        )
    
    with op.batch_alter_table("accounts", schema=None) as batch_op:
        batch_op.alter_column('name', nullable=False)
        batch_op.alter_column('account_type', nullable=False)
        batch_op.create_check_constraint(
            "ck_accounts_current_balance_valid",
            "current_balance IS NULL OR current_balance >= 0"
        )
        batch_op.create_check_constraint(
            "ck_accounts_available_balance_valid",
            "available_balance IS NULL OR available_balance >= 0"
        )
    
    with op.batch_alter_table("holdings", schema=None) as batch_op:
        batch_op.alter_column('symbol', nullable=False)
        batch_op.alter_column('name', nullable=False)
        batch_op.alter_column('quantity', nullable=False)
        batch_op.alter_column('market_value', nullable=False)
        batch_op.create_check_constraint(
            "ck_holdings_quantity_valid",
            "quantity >= 0"
        )
        batch_op.create_check_constraint(
            "ck_holdings_market_value_valid",
            "market_value >= 0"
        )
        batch_op.create_check_constraint(
            "ck_holdings_unit_price_valid",
            "unit_price IS NULL OR unit_price >= 0"
        )
        batch_op.create_unique_constraint(
            "uq_holdings_account_symbol",
            ['account_id', 'symbol']
        )
    
    with op.batch_alter_table("transactions", schema=None) as batch_op:
        batch_op.alter_column('description', nullable=False)
        batch_op.alter_column('date', nullable=False)
        batch_op.alter_column('amount', nullable=False)
        batch_op.create_check_constraint(
            "ck_transactions_quantity_valid",
            "quantity IS NULL OR quantity >= 0"
        )
        batch_op.create_check_constraint(
            "ck_transactions_unit_price_valid",
            "unit_price IS NULL OR unit_price >= 0"
        )
        batch_op.create_check_constraint(
            "ck_transactions_fee_valid",
            "fee IS NULL OR fee >= 0"
        )
    
    # Add constraints for orders table if it exists
    try:
        with op.batch_alter_table("orders", schema=None) as batch_op:
            batch_op.create_check_constraint(
                "ck_orders_quantity_positive",
                "quantity > 0"
            )
            batch_op.create_check_constraint(
                "ck_orders_filled_quantity_valid",
                "filled_quantity >= 0 AND filled_quantity <= quantity"
            )
            batch_op.create_check_constraint(
                "ck_orders_prices_positive",
                "limit_price IS NULL OR limit_price > 0"
            )
            batch_op.create_check_constraint(
                "ck_orders_stop_price_positive",
                "stop_price IS NULL OR stop_price > 0"
            )
            batch_op.create_check_constraint(
                "ck_orders_trail_percent_valid",
                "trail_percent IS NULL OR (trail_percent > 0 AND trail_percent <= 1)"
            )
    except Exception:
        # Orders table might not exist yet
        pass


def downgrade() -> None:
    # Remove constraints in reverse order
    try:
        with op.batch_alter_table("orders", schema=None) as batch_op:
            batch_op.drop_constraint("ck_orders_trail_percent_valid", type_="check")
            batch_op.drop_constraint("ck_orders_stop_price_positive", type_="check")
            batch_op.drop_constraint("ck_orders_prices_positive", type_="check")
            batch_op.drop_constraint("ck_orders_filled_quantity_valid", type_="check")
            batch_op.drop_constraint("ck_orders_quantity_positive", type_="check")
    except Exception:
        pass
    
    with op.batch_alter_table("transactions", schema=None) as batch_op:
        batch_op.drop_constraint("ck_transactions_fee_valid", type_="check")
        batch_op.drop_constraint("ck_transactions_unit_price_valid", type_="check")
        batch_op.drop_constraint("ck_transactions_quantity_valid", type_="check")
    
    with op.batch_alter_table("holdings", schema=None) as batch_op:
        batch_op.drop_constraint("uq_holdings_account_symbol", type_="unique")
        batch_op.drop_constraint("ck_holdings_unit_price_valid", type_="check")
        batch_op.drop_constraint("ck_holdings_market_value_valid", type_="check")
        batch_op.drop_constraint("ck_holdings_quantity_valid", type_="check")
    
    with op.batch_alter_table("accounts", schema=None) as batch_op:
        batch_op.drop_constraint("ck_accounts_available_balance_valid", type_="check")
        batch_op.drop_constraint("ck_accounts_current_balance_valid", type_="check")
    
    with op.batch_alter_table("portfolios", schema=None) as batch_op:
        batch_op.drop_constraint("uq_portfolios_user_name", type_="unique")
    
    with op.batch_alter_table("strategy_holdings", schema=None) as batch_op:
        batch_op.drop_constraint("uq_strategy_holdings_strategy_symbol", type_="unique")
        batch_op.drop_constraint("ck_strategy_holdings_target_weight_valid", type_="check")
    
    with op.batch_alter_table("strategies", schema=None) as batch_op:
        batch_op.drop_constraint("ck_strategies_rebalance_threshold_positive", type_="check")
