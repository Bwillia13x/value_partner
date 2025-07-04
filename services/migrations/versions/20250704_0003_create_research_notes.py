"""create research notes table

Revision ID: 0003
Revises: 0002
Create Date: 2025-07-04 07:00:00.000000
"""

from alembic import op
import sqlalchemy as sa

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'research_notes',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('symbol', sa.String, nullable=False, index=True),
        sa.Column('version', sa.Integer, nullable=False),
        sa.Column('content', sa.String, nullable=False),
        sa.Column('snapshot', sa.JSON),
        sa.Column('created_at', sa.DateTime),
    )


def downgrade() -> None:
    op.drop_table('research_notes')