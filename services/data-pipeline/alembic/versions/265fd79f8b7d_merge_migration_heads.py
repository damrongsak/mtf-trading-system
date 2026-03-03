"""Merge migration heads

Revision ID: 265fd79f8b7d
Revises: a4ce88bcc407, a8f3c9e2d1b4
Create Date: 2026-02-22 03:33:42.639944

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '265fd79f8b7d'
down_revision: Union[str, Sequence[str], None] = ('a4ce88bcc407', 'a8f3c9e2d1b4')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
