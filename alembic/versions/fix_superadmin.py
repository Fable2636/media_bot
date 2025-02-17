"""fix superadmin

Revision ID: fix_superadmin
Revises: add_superadmin_field
Create Date: 2024-02-16 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'fix_superadmin'
down_revision = 'add_superadmin_field'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Сначала сбрасываем все флаги суперадмина
    op.execute("""
        UPDATE users 
        SET is_superadmin = 0 
        WHERE is_superadmin IS NOT NULL
    """)
    
    # Устанавливаем суперадмина
    op.execute("""
        UPDATE users 
        SET is_superadmin = 1, is_admin = 1
        WHERE telegram_id = 787676749
    """)

def downgrade() -> None:
    op.execute("""
        UPDATE users 
        SET is_superadmin = 0 
        WHERE telegram_id = 787676749
    """) 