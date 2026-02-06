"""Add details column to MarketSymbol

Revision ID: 99fdf29e571a
Revises: afae1460db4d
Create Date: 2026-01-14 04:25:03.467281

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '99fdf29e571a'
down_revision = 'afae1460db4d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Column already exists in DB from previous external migrations
    pass


def downgrade() -> None:
    # Column already exists in DB
    pass
