"""add previous_status to submissions

Revision ID: c929d32e2791
Revises: update_submission_statuses
Create Date: 2025-02-01 13:26:48.861311

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c929d32e2791'
down_revision: Union[str, None] = 'update_submission_statuses'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Создаем новую таблицу
    op.create_table('submissions_new',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('photo', sa.String(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('previous_status', sa.Enum('PENDING', 'TEXT_APPROVED', 'PHOTO_PENDING', 'APPROVED', 'REVISION', 'COMPLETED', name='submissionstatus'), nullable=True),
        sa.Column('revision_comment', sa.Text(), nullable=True),
        sa.Column('published_link', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Копируем данные
    op.execute('''
        INSERT INTO submissions_new (
            id, task_id, user_id, content, photo, submitted_at, 
            status, revision_comment, published_link
        )
        SELECT id, task_id, user_id, content, photo, submitted_at, 
               status, revision_comment, published_link
        FROM submissions
    ''')
    
    # Удаляем старую таблицу
    op.drop_table('submissions')
    
    # Переименовываем новую таблицу
    op.rename_table('submissions_new', 'submissions')
    
    # Создаем индекс
    op.create_index(op.f('ix_submissions_id'), 'submissions', ['id'], unique=False)


def downgrade() -> None:
    # При даунгрейде просто удаляем колонку previous_status
    # Создаем новую таблицу без previous_status
    op.create_table('submissions_new',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=True),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('content', sa.String(), nullable=True),
        sa.Column('photo', sa.String(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('revision_comment', sa.String(), nullable=True),
        sa.Column('published_link', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Копируем данные
    op.execute('''
        INSERT INTO submissions_new (
            id, task_id, user_id, content, photo, submitted_at, 
            status, revision_comment, published_link
        )
        SELECT id, task_id, user_id, content, photo, submitted_at, 
               status, revision_comment, published_link
        FROM submissions
    ''')
    
    # Удаляем старую таблицу
    op.drop_table('submissions')
    
    # Переименовываем новую таблицу
    op.rename_table('submissions_new', 'submissions')