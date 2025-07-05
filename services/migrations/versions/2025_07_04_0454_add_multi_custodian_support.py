"""Add multi-custodian support

Revision ID: 2025_07_04_0454
Revises: 
Create Date: 2025-07-04 04:54:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '2025_07_04_0454'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create custodian table
    op.create_table(
        'custodians',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('display_name', sa.String(length=200), nullable=True),
        sa.Column('logo_url', sa.String(length=500), nullable=True),
        sa.Column('website', sa.String(length=200), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='1', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), 
                 nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    
    # Create portfolios table
    op.create_table(
        'portfolios',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_primary', sa.Boolean(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP'), 
                 nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add columns to accounts table
    op.add_column('accounts', sa.Column('custodian_id', sa.Integer(), nullable=True))
    op.add_column('accounts', sa.Column('portfolio_id', sa.Integer(), nullable=True))
    op.add_column('accounts', sa.Column('external_id', sa.String(length=100), nullable=True))
    op.add_column('accounts', sa.Column('is_manual', sa.Boolean(), server_default='0', nullable=False))
    op.add_column('accounts', sa.Column('last_synced_at', sa.DateTime(), nullable=True))
    
    # Create foreign key constraints
    op.create_foreign_key(
        'fk_accounts_custodian_id_custodians',
        'accounts', 'custodians',
        ['custodian_id'], ['id'],
        ondelete='SET NULL'
    )
    
    op.create_foreign_key(
        'fk_accounts_portfolio_id_portfolios',
        'accounts', 'portfolios',
        ['portfolio_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # Create index for better query performance
    op.create_index(op.f('ix_accounts_custodian_id'), 'accounts', ['custodian_id'], unique=False)
    op.create_index(op.f('ix_accounts_portfolio_id'), 'accounts', ['portfolio_id'], unique=False)
    op.create_index(op.f('ix_accounts_external_id'), 'accounts', ['external_id'], unique=False)
    
    # Add any default custodians
    op.execute("""
        INSERT INTO custodians (name, display_name, website, is_active)
        VALUES 
            ('plaid', 'Plaid', 'https://plaid.com', 1),
            ('alpaca', 'Alpaca', 'https://alpaca.markets', 1),
            ('manual', 'Manual Entry', NULL, 1)
    """)

def downgrade():
    # Drop foreign key constraints first
    op.drop_constraint('fk_accounts_portfolio_id_portfolios', 'accounts', type_='foreignkey')
    op.drop_constraint('fk_accounts_custodian_id_custodians', 'accounts', type_='foreignkey')
    
    # Drop indexes
    op.drop_index(op.f('ix_accounts_external_id'), table_name='accounts')
    op.drop_index(op.f('ix_accounts_portfolio_id'), table_name='accounts')
    op.drop_index(op.f('ix_accounts_custodian_id'), table_name='accounts')
    
    # Drop columns from accounts
    op.drop_column('accounts', 'last_synced_at')
    op.drop_column('accounts', 'is_manual')
    op.drop_column('accounts', 'external_id')
    op.drop_column('accounts', 'portfolio_id')
    op.drop_column('accounts', 'custodian_id')
    
    # Drop tables
    op.drop_table('portfolios')
    op.drop_table('custodians')
