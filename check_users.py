import sqlite3

def check_users():
    conn = sqlite3.connect('media_bot.db')
    cursor = conn.cursor()
    
    print("=== Все пользователи в базе данных ===")
    cursor.execute('''
        SELECT telegram_id, username, is_admin, is_superadmin, media_outlet 
        FROM users
    ''')
    users = cursor.fetchall()
    
    for user in users:
        print(f"""
Telegram ID: {user[0]}
Username: {user[1]}
is_admin: {user[2]}
is_superadmin: {user[3]}
media_outlet: {user[4]}
-------------------""")
    
    conn.close()

if __name__ == '__main__':
    check_users() 