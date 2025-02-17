"""add superadmin field

Revision ID: add_superadmin_field
Revises: c929d32e2791
Create Date: 2024-02-16 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'add_superadmin_field'
down_revision = 'c929d32e2791'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Добавляем поле is_superadmin
    op.add_column('users', sa.Column('is_superadmin', sa.Boolean(), nullable=True, default=False))
    
    # Устанавливаем первого админа как суперадмина
    op.execute("""
        UPDATE users 
        SET is_superadmin = 1 
        WHERE telegram_id = 787676749
    """)

def downgrade() -> None:
    # Удаляем поле is_superadmin
    op.drop_column('users', 'is_superadmin') 