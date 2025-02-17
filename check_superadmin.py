import sqlite3

def check_user():
    conn = sqlite3.connect('media_bot.db')
    cursor = conn.cursor()
    
    # Проверяем существование таблицы и колонки
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='users';
    """)
    if not cursor.fetchone():
        print("Таблица users не существует!")
        return
        
    cursor.execute('PRAGMA table_info(users);')
    columns = [col[1] for col in cursor.fetchall()]
    print("Колонки в таблице users:", columns)
    
    # Проверяем данные пользователя
    cursor.execute('''
        SELECT telegram_id, username, is_admin, is_superadmin 
        FROM users 
        WHERE telegram_id = 787676749
    ''')
    result = cursor.fetchone()
    if result:
        print(f"""
Данные пользователя:
Telegram ID: {result[0]}
Username: {result[1]}
is_admin: {result[2]}
is_superadmin: {result[3]}
""")
    else:
        print("Пользователь не найден!")
    
    conn.close()

if __name__ == '__main__':
    check_user() 