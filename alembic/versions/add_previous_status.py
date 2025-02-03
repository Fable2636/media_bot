"""add previous status

Revision ID: add_previous_status
Revises: 
Create Date: 2025-02-01 13:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_previous_status'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # SQLite не поддерживает ALTER COLUMN, поэтому создаем новую таблицу
    op.execute('''
        CREATE TABLE submissions_new (
            id INTEGER PRIMARY KEY,
            task_id INTEGER REFERENCES tasks(id),
            user_id INTEGER REFERENCES users(id),
            content TEXT,
            photo TEXT,
            submitted_at TIMESTAMP,
            status VARCHAR,
            previous_status VARCHAR,
            revision_comment TEXT,
            published_link TEXT
        )
    ''')
    
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
    op.execute('DROP TABLE submissions')
    
    # Переименовываем новую таблицу
    op.execute('ALTER TABLE submissions_new RENAME TO submissions')

def downgrade():
    # SQLite не поддерживает ALTER COLUMN, поэтому создаем новую таблицу без previous_status
    op.execute('''
        CREATE TABLE submissions_new (
            id INTEGER PRIMARY KEY,
            task_id INTEGER REFERENCES tasks(id),
            user_id INTEGER REFERENCES users(id),
            content TEXT,
            photo TEXT,
            submitted_at TIMESTAMP,
            status VARCHAR,
            revision_comment TEXT,
            published_link TEXT
        )
    ''')
    
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
    op.execute('DROP TABLE submissions')
    
    # Переименовываем новую таблицу
    op.execute('ALTER TABLE submissions_new RENAME TO submissions') 