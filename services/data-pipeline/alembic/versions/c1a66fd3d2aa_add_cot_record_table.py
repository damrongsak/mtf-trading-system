"""Add COT Record table

Revision ID: c1a66fd3d2aa
Revises: 36321cdd9c03
Create Date: 2026-02-19 09:42:36.851468

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c1a66fd3d2aa'
down_revision = '36321cdd9c03'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'cot_records',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('report_date', sa.DateTime(), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('commercials_long', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('commercials_short', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('non_commercials_long', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('non_commercials_short', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('managed_money_long', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('managed_money_short', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('non_reportable_long', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('non_reportable_short', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('symbol', 'report_date', name='uq_cot_records_symbol_report_date')
    )
    op.create_index('ix_cot_records_report_date', 'cot_records', ['report_date'], unique=False)
    op.create_index('ix_cot_records_symbol', 'cot_records', ['symbol'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_cot_records_symbol', table_name='cot_records')
    op.drop_index('ix_cot_records_report_date', table_name='cot_records')
    op.drop_table('cot_records')
