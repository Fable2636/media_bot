"""check users

Revision ID: check_users
Revises: add_all_users
Create Date: 2024-02-16 14:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = 'check_users'
down_revision = 'add_all_users'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Используем text() для создания выполняемого SQL-запроса
    connection = op.get_bind()
    result = connection.execute(text("""
        SELECT telegram_id, username, is_admin, is_superadmin, media_outlet 
        FROM users
    """))
    
    for row in result:
        print(f"User {row.username} (ID: {row.telegram_id})")
        print(f"Admin: {row.is_admin}, Superadmin: {row.is_superadmin}")
        print(f"Media outlet: {row.media_outlet}")
        print("---")

def downgrade() -> None:
    pass 