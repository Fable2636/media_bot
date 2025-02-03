"""update submission statuses

Revision ID: update_submission_statuses
Revises: 4123f024fee0
Create Date: 2024-02-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'update_submission_statuses'
down_revision = '4123f024fee0'

def upgrade() -> None:
    # Обновляем существующие статусы
    op.execute("""
        UPDATE submissions 
        SET status = 'text_approved' 
        WHERE status = 'approved' AND photo IS NULL
    """)
    op.execute("""
        UPDATE submissions 
        SET status = 'photo_pending' 
        WHERE status = 'pending' AND photo IS NOT NULL
    """)

def downgrade() -> None:
    # Возвращаем старые статусы
    op.execute("""
        UPDATE submissions 
        SET status = 'pending' 
        WHERE status IN ('text_approved', 'photo_pending')
    """) 