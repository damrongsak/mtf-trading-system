"""feat: add hierarchical risk filters

Revision ID: fe4b9c1d2e3f
Revises: consolidated_head_v1
Create Date: 2026-03-03 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'fe4b9c1d2e3f'
down_revision = 'consolidated_head_v1'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table('risk_filters',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('target_type', sa.Enum('SYSTEM', 'FUND', 'BROKER_ACCOUNT', 'STRATEGY', name='target_type_enum'), nullable=False),
        sa.Column('target_id', sa.UUID(), nullable=True),
        sa.Column('filter_type', sa.String(length=50), nullable=False),
        sa.Column('is_enabled', sa.Boolean(), nullable=True),
        sa.Column('threshold_parameters', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('target_type', 'target_id', 'filter_type', name='uq_risk_filter_target_type_id')
    )
    op.create_index(op.f('ix_risk_filters_filter_type'), 'risk_filters', ['filter_type'], unique=False)
    op.create_index(op.f('ix_risk_filters_target_id'), 'risk_filters', ['target_id'], unique=False)
    op.create_index(op.f('ix_risk_filters_target_type'), 'risk_filters', ['target_type'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_risk_filters_target_type'), table_name='risk_filters')
    op.drop_index(op.f('ix_risk_filters_target_id'), table_name='risk_filters')
    op.drop_index(op.f('ix_risk_filters_filter_type'), table_name='risk_filters')
    op.drop_table('risk_filters')
    op.execute("DROP TYPE IF EXISTS target_type_enum")
