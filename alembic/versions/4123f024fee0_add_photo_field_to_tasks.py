"""add_photo_field_to_tasks

Revision ID: 4123f024fee0
Revises: d5806289c82c
Create Date: 2025-01-29 10:09:52.131290

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4123f024fee0'
down_revision: Union[str, None] = 'd5806289c82c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Проверяем, существует ли колонка photo
    inspector = sa.inspect(op.get_bind())
    columns = [col['name'] for col in inspector.get_columns('tasks')]
    if 'photo' not in columns:
        op.add_column('tasks', sa.Column('photo', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('tasks', 'photo')