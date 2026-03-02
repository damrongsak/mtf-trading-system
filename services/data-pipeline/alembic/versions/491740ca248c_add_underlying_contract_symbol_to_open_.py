"""Add underlying_contract_symbol to open_interest

Revision ID: 491740ca248c
Revises: c1a66fd3d2aa
Create Date: 2026-03-02 10:09:08.459828

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '491740ca248c'
down_revision = 'c1a66fd3d2aa'
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
