"""add all users

Revision ID: add_all_users
Revises: fix_superadmin
Create Date: 2024-02-16 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = 'add_all_users'
down_revision = 'fix_superadmin'
branch_labels = None
depends_on = None

# Определяем пользователей здесь для независимости миграции
ADMINS = [
    {
        "telegram_id": 148279040,
        "username": "saiga30"
    },
    {
        "telegram_id": 787676749,
        "username": "Fable2636"
    },
    {
        "telegram_id": 748042460,
        "username": "+7 (917) 187-15-02"
    },
    {
        "telegram_id": 1761115242,
        "username": "AlinaDzhetenova"
    },
    {
        "telegram_id": 1072950255,
        "username": "Lavandaastra"
    },
    {
        "telegram_id": 893044294,
        "username": "+7 (961) 655-43-15"
    },
    {
        "telegram_id": 1381162664,
        "username": "@pdgrn"
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
    },
    {
        "telegram_id": 94697652,
        "username": "@AngelinaSergeevna",
        "media_outlet": "Второй канал"
    },
    {
        "telegram_id": 83851741,
        "username": "@rrrrr30",
        "media_outlet": "Второй канал"
    }
]

def upgrade() -> None:
    # Добавляем админов
    for admin in ADMINS:
        op.execute(f"""
            INSERT OR IGNORE INTO users (telegram_id, username, is_admin, is_superadmin)
            VALUES ({admin['telegram_id']}, '{admin['username']}', 1, 0)
        """)
    
    # Устанавливаем суперадмина
    op.execute("""
        UPDATE users 
        SET is_superadmin = 1 
        WHERE telegram_id = 787676749
    """)
    
    # Добавляем представителей СМИ
    for media in MEDIA_OUTLETS:
        op.execute(f"""
            INSERT OR IGNORE INTO users (telegram_id, username, is_admin, is_superadmin, media_outlet)
            VALUES (
                {media['telegram_id']}, 
                '{media['username']}', 
                0, 
                0,
                '{media['media_outlet']}'
            )
        """)

def downgrade() -> None:
    # В случае отката удаляем всех пользователей
    op.execute("DELETE FROM users") 