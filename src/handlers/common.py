from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, User
from src.keyboards.admin_kb import get_admin_main_keyboard
from src.keyboards.media_kb import get_media_main_keyboard
from src.keyboards.common_kb import get_start_keyboard
from src.utils.check_admin import check_admin
import logging

# Создаем роутер с именем
router = Router(name='common')

@router.message(Command("start"))
async def handle_start_command(message: Message, user: User):
    try:
        logging.info("=" * 50)
        logging.info("START COMMAND HANDLER")
        logging.info(f"Start command from user {message.from_user.id}")
        
        if not user:
            logging.error("User object is None!")
            return
        
        is_admin = await check_admin(user)
        logging.info(f"User {user.telegram_id} is_admin: {is_admin}")
        
        if is_admin:
            logging.info("SENDING ADMIN KEYBOARD")
            await message.answer(
                "Добро пожаловать в панель администратора!",
                reply_markup=get_admin_main_keyboard()
            )
        else:
            logging.info("SENDING MEDIA KEYBOARD")
            await message.answer(
                "Добро пожаловать в систему управления публикациями!",
                reply_markup=get_media_main_keyboard()
            )
        
    except Exception as e:
        logging.error(f"Error in start command: {e}", exc_info=True)
        raise

    logging.info("START COMMAND HANDLER FINISHED")
    logging.info("=" * 50)