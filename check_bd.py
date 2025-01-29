import sqlite3

def check_database_schema(db_path: str = 'media_bot.db'):
    """Проверяет схему базы данных и выводит все таблицы и их столбцы."""
    try:
        # Подключаемся к базе данных
        conn = sqlite3.connect('media_bot.db')
        cursor = conn.cursor()

        # Получаем список всех таблиц
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()

        # Для каждой таблицы получаем информацию о столбцах
        for table in tables:
            table_name = table[0]
            print(f"Таблица: {table_name}")
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            for column in columns:
                print(f"  Столбец: {column[1]} (Тип: {column[2]}, Nullable: {column[3]}, Primary Key: {column[5]})")
            print()  # Пустая строка для разделения таблиц

    except sqlite3.Error as e:
        print(f"Ошибка при проверке базы данных: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    check_database_schema() 