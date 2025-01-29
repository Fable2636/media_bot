import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums.parse_mode import ParseMode
from dotenv import load_dotenv
import os
from pathlib import Path
from aiogram.client.default import DefaultBotProperties
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from src.config.bot_config import BOT_TOKEN, DATABASE_URL

from src.handlers import admin, media, common, set_commands
from src.middlewares.auth import AuthMiddleware
from src.middlewares.db_middleware import DbSessionMiddleware
from src.middlewares.user_middleware import UserMiddleware
from src.utils.logger import setup_logger
from src.database.engine import engine
from src.database.base import Base
from aiogram import Router

logger = setup_logger()
load_dotenv()

async def main():
    # Настраиваем логирование
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler("bot.log"),
            logging.StreamHandler()
        ]
    )
    
    # Инициализация бота и диспетчера
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Инициализация сессии базы данных
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    
    # Добавляем middleware
    dp.update.middleware(DbSessionMiddleware(session_pool=async_session))
    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(UserMiddleware())
    
    # Регистрация роутеров
    dp.include_router(admin.router)
    dp.include_router(media.router)
    dp.include_router(common.router)
    
    # Добавляем бота в данные диспетчера
    dp["bot"] = bot
    
    # Устанавливаем команды бота
    await set_commands(bot, async_session)
    
    logging.info("Starting bot...")
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Ошибка при запуске бота: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())