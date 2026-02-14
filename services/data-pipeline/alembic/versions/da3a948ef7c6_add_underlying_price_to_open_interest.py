"""Add underlying_price to open_interest

Revision ID: da3a948ef7c6
Revises: 97219bf0d3ff
Create Date: 2026-02-14 01:55:25.549221

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'da3a948ef7c6'
down_revision = '97219bf0d3ff'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('open_interest', sa.Column('underlying_price', sa.Numeric(precision=18, scale=8), nullable=True))


def downgrade() -> None:
    op.drop_column('open_interest', 'underlying_price')
