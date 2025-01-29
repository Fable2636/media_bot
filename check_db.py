import sqlite3
from datetime import datetime

def check_database():
    print("Подключение к базе данных...")
    try:
        conn = sqlite3.connect('media_bot.db')
        cursor = conn.cursor()
        
        # Проверяем существование таблиц
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print("\nСуществующие таблицы:", [table[0] for table in tables])
        
        print("\nПроверка таблицы users:")
        try:
            cursor.execute("SELECT * FROM users")
            users = cursor.fetchall()
            if users:
                print("Найдены пользователи:")
                for user in users:
                    print(f"ID: {user[0]}, Telegram ID: {user[1]}, Username: {user[2]}, Is Admin: {user[3]}, Media Outlet: {user[4]}")
            else:
                print("Пользователи не найдены")
        except sqlite3.OperationalError as e:
            print(f"Ошибка при проверке users: {e}")
        
        print("\nПроверка таблицы submissions:")
        try:
            cursor.execute("SELECT * FROM submissions")
            submissions = cursor.fetchall()
            if submissions:
                print("Найдены публикации:")
                for sub in submissions:
                    print(f"ID: {sub[0]}, Task ID: {sub[1]}, User ID: {sub[2]}, Status: {sub[5]}")
            else:
                print("Публикации не найдены")
        except sqlite3.OperationalError as e:
            print(f"Ошибка при проверке submissions: {e}")
        
        # Проверяем структуру таблицы tasks
        cursor.execute("PRAGMA table_info(tasks)")
        columns = cursor.fetchall()
        print("\nТаблица tasks:")
        for col in columns:
            print(f"  Столбец: {col[1]}, Тип: {col[2]}, Nullable: {col[3]}, Primary Key: {col[5]}")
        
    except Exception as e:
        print(f"Ошибка при подключении к базе данных: {e}")
    finally:
        conn.close()

def check_tasks():
    conn = sqlite3.connect('media_bot.db')
    cursor = conn.cursor()
    
    # Проверяем данные в таблице tasks
    cursor.execute("SELECT id, press_release_link, photo FROM tasks")
    tasks = cursor.fetchall()
    
    print("Задания в базе данных:")
    for task in tasks:
        print(f"ID: {task[0]}, Ссылка: {task[1]}, Фото: {'Есть' if task[2] else 'Нет'}")
    
    conn.close()

if __name__ == "__main__":
    check_database()
    check_tasks() 