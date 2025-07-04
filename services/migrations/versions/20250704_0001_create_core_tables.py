"""create core financial tables

Revision ID: 0001
Revises: 
Create Date: 2025-07-04 05:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'financial_statements',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('symbol', sa.String, nullable=False, index=True),
        sa.Column('period_type', sa.Enum('quarterly', 'annual', name='period_type'), nullable=False),
        sa.Column('fiscal_period', sa.String, nullable=False),
        sa.Column('statement_type', sa.Enum('IS', 'BS', 'CF', name='statement_type'), nullable=False),
        sa.Column('data', sa.JSON, nullable=False),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('now()')),
    )

    op.create_table(
        'key_metrics',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('symbol', sa.String, nullable=False, index=True),
        sa.Column('metric_name', sa.String, nullable=False),
        sa.Column('value', sa.Float),
        sa.Column('period', sa.String),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('now()')),
    )

    op.create_table(
        'intrinsic_valuations',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('symbol', sa.String, nullable=False, index=True),
        sa.Column('valuation_type', sa.String, nullable=False),
        sa.Column('base_value', sa.Float),
        sa.Column('bear_value', sa.Float),
        sa.Column('bull_value', sa.Float),
        sa.Column('as_of_date', sa.DateTime),
        sa.Column('inputs', sa.JSON),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('now()')),
    )

    op.create_table(
        'qualitative_signals',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('symbol', sa.String, nullable=False, index=True),
        sa.Column('signal_type', sa.String, nullable=False),
        sa.Column('score', sa.Float),
        sa.Column('data', sa.JSON),
        sa.Column('as_of_date', sa.DateTime),
        sa.Column('created_at', sa.DateTime, server_default=sa.text('now()')),
    )


def downgrade() -> None:
    op.drop_table('qualitative_signals')
    op.drop_table('intrinsic_valuations')
    op.drop_table('key_metrics')
    op.drop_table('financial_statements')