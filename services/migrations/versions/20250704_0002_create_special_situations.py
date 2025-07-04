"""create special situations table

Revision ID: 0002
Revises: 0001
Create Date: 2025-07-04 06:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'special_situations',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('symbol', sa.String, nullable=False, index=True),
        sa.Column('filing_type', sa.String, nullable=False),
        sa.Column('filed_at', sa.DateTime),
        sa.Column('url', sa.String),
        sa.Column('data', sa.JSON),
        sa.Column('created_at', sa.DateTime),
    )


def downgrade() -> None:
    op.drop_table('special_situations')