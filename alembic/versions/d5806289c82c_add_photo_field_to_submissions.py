"""add photo field to submissions

Revision ID: d5806289c82c
Revises: 34c9bab90e35
Create Date: 2025-01-28 10:03:42.780966

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd5806289c82c'
down_revision: Union[str, None] = '34c9bab90e35'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    # Добавляем поле photo в таблицу submissions
    op.add_column('submissions', sa.Column('photo', sa.String(), nullable=True))

def downgrade():
    # Удаляем поле photo из таблицы submissions
    op.drop_column('submissions', 'photo')