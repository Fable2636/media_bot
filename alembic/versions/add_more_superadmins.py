"""add more superadmins

Revision ID: add_more_superadmins
Revises: add_all_users
Create Date: 2024-02-16 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'add_more_superadmins'
down_revision = 'add_all_users'
branch_labels = None
depends_on = None

# Список ID пользователей, которых нужно сделать суперадминами
SUPERADMIN_IDS = [
    787676749,  # Существующий суперадмин
    148279040,  # Добавьте сюда ID дополнительных суперадминов
]

def upgrade() -> None:
    # Сначала сбрасываем все флаги суперадмина
    op.execute("""
        UPDATE users 
        SET is_superadmin = 0 
        WHERE is_superadmin IS NOT NULL
    """)
    
    # Устанавливаем новых суперадминов
    for admin_id in SUPERADMIN_IDS:
        op.execute(f"""
            UPDATE users 
            SET is_superadmin = 1, is_admin = 1
            WHERE telegram_id = {admin_id}
        """)

def downgrade() -> None:
    # При откате оставляем только одного суперадмина
    op.execute("""
        UPDATE users 
        SET is_superadmin = 0 
        WHERE telegram_id != 787676749
    """) 