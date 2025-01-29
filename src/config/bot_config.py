import os
from dotenv import load_dotenv
from pathlib import Path

# Получаем путь к директории проекта
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Загружаем .env файл
load_dotenv(BASE_DIR / '.env')

# Загружаем токен бота из переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в переменных окружения")

# URL для подключения к базе данных SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///media_bot.db") 