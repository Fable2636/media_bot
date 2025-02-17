"""initial

Revision ID: 34c9bab90e35
Revises: 
Create Date: 2025-01-22 21:15:25.803491

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '34c9bab90e35'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Определяем данные здесь вместо импорта
ADMINS = [
    {
        "telegram_id": 148279040,
        "username": "saiga30"
    },
    {
        "telegram_id": 787676749,
        "username": "Fable2636"
    }
]

MEDIA_OUTLETS = [
    {
        "telegram_id": 157648462,
        "username": "@Kolesnikov15",
        "media_outlet": "Первый канал"
    },
    {
        "telegram_id": 401400389,
        "username": "Fable0309",
        "media_outlet": "Первый канал"
    }
]

def upgrade() -> None:
    # Создаем таблицу users
    users = op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('telegram_id', sa.Integer(), nullable=True),
        sa.Column('username', sa.String(), nullable=True),
        sa.Column('is_admin', sa.Integer(), nullable=False),
        sa.Column('media_outlet', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_telegram_id'), 'users', ['telegram_id'], unique=True)

    # Добавляем админов
    op.bulk_insert(users, [
        {
            'telegram_id': admin['telegram_id'],
            'username': admin['username'],
            'is_admin': 1,
            'media_outlet': None
        }
        for admin in ADMINS
    ])

    # Добавляем СМИ
    op.bulk_insert(users, [
        {
            'telegram_id': media['telegram_id'],
            'username': media['username'],
            'is_admin': 0,
            'media_outlet': media['media_outlet']
        }
        for media in MEDIA_OUTLETS
    ])

    # Создаем таблицу tasks с полем photo
    op.create_table('tasks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('press_release_link', sa.String(), nullable=True),
        sa.Column('deadline', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('photo', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Создаем остальные таблицы...
    op.create_table('submissions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('content', sa.String(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('revision_comment', sa.String(), nullable=True),
        sa.Column('published_link', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_table('task_assignments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=True),
        sa.Column('media_outlet', sa.String(), nullable=True),
        sa.Column('assigned_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade() -> None:
    op.drop_table('task_assignments')
    op.drop_table('submissions')
    op.drop_table('tasks')
    op.drop_index(op.f('ix_users_telegram_id'), table_name='users')
    op.drop_table('users')