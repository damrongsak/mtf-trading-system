"""fix_lot_size_constraint_manual

Revision ID: 4eb2b4c9456e
Revises: e8621a66f966
Create Date: 2025-12-12 00:32:06.145569

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4eb2b4c9456e'
down_revision: Union[str, Sequence[str], None] = 'e8621a66f966'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
