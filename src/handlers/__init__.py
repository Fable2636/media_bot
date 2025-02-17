from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeChat
from src.config.users import ADMINS
from src.services.user_service import UserService
from sqlalchemy.ext.asyncio import async_sessionmaker

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
            for admin in ADMINS:
                try:
                    # Проверяем, существует ли пользователь в базе
                    user = await user_service.get_user_by_telegram_id(admin["telegram_id"])
                    if user:
                        # Выбираем набор команд в зависимости от статуса пользователя
                        commands = superadmin_commands if user.is_superadmin else admin_commands
                        await bot.set_my_commands(commands, scope=BotCommandScopeChat(chat_id=admin["telegram_id"]))
                    else:
                        print(f"Пользователь {admin['username']} (ID: {admin['telegram_id']}) не найден в базе данных")
                except Exception as e:
                    print(f"Не удалось установить команды для администратора {admin['username']} (ID: {admin['telegram_id']}): {e}")
        
    except Exception as e:
        print(f"Ошибка при установке команд: {e}")

# Экспортируем функцию
__all__ = ["set_commands"]
