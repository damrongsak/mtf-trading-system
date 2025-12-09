"""Initial migration

Revision ID: 4833c32da739
Revises: 
Create Date: 2025-12-09 04:32:24.334561

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '4833c32da739'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # This migration should not drop any tables, as other services manage them.
    # It primarily serves to establish a base revision for this service.
    pass


def downgrade() -> None:
    # Revert the changes made in upgrade.
    # If upgrade was a no-op, downgrade should also be a no-op.
    pass
