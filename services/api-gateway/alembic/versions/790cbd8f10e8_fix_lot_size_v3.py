"""fix_lot_size_v3

Revision ID: 790cbd8f10e8
Revises: 4eb2b4c9456e
Create Date: 2025-12-12 01:54:17.243523

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "790cbd8f10e8"
down_revision: Union[str, Sequence[str], None] = "4eb2b4c9456e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint("check_min_lot_size", "trades", type_="check")
    op.create_check_constraint("check_min_lot_size", "trades", "lot_size > 0")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("check_min_lot_size", "trades", type_="check")
    op.create_check_constraint("check_min_lot_size", "trades", "lot_size >= 0.01")
