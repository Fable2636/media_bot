import sqlite3

def check_admin():
    conn = sqlite3.connect('media_bot.db')
    cursor = conn.cursor()
    
    cursor.execute("""
        UPDATE users 
        SET is_admin = 1 
        WHERE telegram_id = 787676749
    """)
    
    conn.commit()
    
    cursor.execute("SELECT * FROM users WHERE telegram_id = 787676749")
    user = cursor.fetchone()
    print(f"Admin user: {user}")
    
    conn.close()

if __name__ == "__main__":
    check_admin() 