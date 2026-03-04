"""merge_heads_v2

Revision ID: merge_heads_v2
Revises: 82acfe2850d1, b2b62c1ce616
Create Date: 2026-03-04 09:20:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'merge_heads_v2'
down_revision = ('82acfe2850d1', 'b2b62c1ce616')
branch_labels = None
depends_on = None

def upgrade():
    pass

def downgrade():
    pass
