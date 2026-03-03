"""Merge heads from api-gateway and data-pipeline

Revision ID: consolidated_head_v1
Revises: 6772ce98e149, 491740ca248c
Create Date: 2026-03-03 18:10:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'consolidated_head_v1'
down_revision = ('6772ce98e149', '491740ca248c')
branch_labels = None
depends_on = None

def upgrade() -> None:
    pass

def downgrade() -> None:
    pass
