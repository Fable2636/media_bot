"""merge heads

Revision ID: merge_heads
Revises: add_more_superadmins, check_users
Create Date: 2024-02-16 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'merge_heads'
down_revision = None
branch_labels = None
depends_on = ('add_more_superadmins', 'check_users')

def upgrade() -> None:
    pass

def downgrade() -> None:
    pass 