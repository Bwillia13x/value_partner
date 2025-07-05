"""Add missing Orders table

Revision ID: dd2b332b3d0d
Revises: 4dd2c2396c7f
Create Date: 2025-07-04 09:45:46.636816

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dd2b332b3d0d'
down_revision: Union[str, None] = '4dd2c2396c7f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create orders table
    op.create_table('orders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('account_id', sa.Integer(), nullable=True),
        sa.Column('strategy_id', sa.Integer(), nullable=True),
        sa.Column('symbol', sa.String(), nullable=False),
        sa.Column('side', sa.Enum('BUY', 'SELL', name='orderside'), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=15, scale=6), nullable=False),
        sa.Column('order_type', sa.Enum('MARKET', 'LIMIT', 'STOP', 'STOP_LIMIT', 'TRAILING_STOP', name='ordertype'), nullable=False),
        sa.Column('time_in_force', sa.Enum('DAY', 'GTC', 'IOC', 'FOK', name='timeinforce'), nullable=True),
        sa.Column('limit_price', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('stop_price', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('trail_percent', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('trail_price', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('filled_quantity', sa.Numeric(precision=15, scale=6), nullable=True),
        sa.Column('average_fill_price', sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column('commission', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('status', sa.Enum('PENDING', 'SUBMITTED', 'PARTIALLY_FILLED', 'FILLED', 'CANCELLED', 'REJECTED', name='orderstatus'), nullable=True),
        sa.Column('broker_order_id', sa.String(), nullable=True),
        sa.Column('client_order_id', sa.String(), nullable=True),
        sa.Column('extended_hours', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), nullable=True),
        sa.Column('filled_at', sa.DateTime(), nullable=True),
        sa.Column('broker_data', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['account_id'], ['accounts.id'], ),
        sa.ForeignKeyConstraint(['strategy_id'], ['strategies.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_orders_id'), 'orders', ['id'], unique=False)


def downgrade() -> None:
    # Drop orders table
    op.drop_index(op.f('ix_orders_id'), table_name='orders')
    op.drop_table('orders')
