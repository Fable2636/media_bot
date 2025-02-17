from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeChat
from sqlalchemy.ext.asyncio import async_sessionmaker
from src.services.user_service import UserService
import logging

async def set_commands(bot: Bot, session_pool: async_sessionmaker):
    try:
        # Устанавливаем команды для всех пользователей
        await bot.set_my_commands([
            BotCommand(command="start", description="Запустить бота"),
            BotCommand(command="help", description="Помощь")
        ])
        
        # Устанавливаем команды для администраторов
        admin_commands = [
            BotCommand(command="admin", description="Админ панель"),
            BotCommand(command="stats", description="Статистика")
        ]
        
        # Команды для суперадмина
        superadmin_commands = admin_commands + [
            BotCommand(command="superadmin", description="Панель суперадмина")
        ]
        
        async with session_pool() as session:
            user_service = UserService(session)
            # Получаем всех админов из базы данных
            admins = await user_service.get_all_admins()
            
            for admin in admins:
                try:
                    # Выбираем набор команд в зависимости от статуса пользователя
                    commands = superadmin_commands if admin.is_superadmin else admin_commands
                    await bot.set_my_commands(
                        commands, 
                        scope=BotCommandScopeChat(chat_id=admin.telegram_id)
                    )
                    logging.info(f"Set commands for admin {admin.username} (ID: {admin.telegram_id})")
                except Exception as e:
                    logging.error(f"Failed to set commands for admin {admin.username} (ID: {admin.telegram_id}): {e}")
        
    except Exception as e:
        logging.error(f"Error setting commands: {e}")

# Экспортируем функцию
__all__ = ["set_commands"]
