from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select, text
from src.database.models import User
import logging

class UserMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        # Добавляем логирование типа события
        logging.info(f"Processing event type: {type(event).__name__}")
        if isinstance(event, Message):
            logging.info(f"Message text: {event.text}")
        
        session = data['session']
        user_id = event.from_user.id
        
        logging.info(f"UserMiddleware: Processing user {user_id}")
        
        try:
            # Выполняем запрос напрямую через SQL для проверки
            result = await session.execute(
                text("SELECT id, telegram_id, username, is_admin, media_outlet FROM users WHERE telegram_id = :user_id"),
                {"user_id": user_id}
            )
            row = result.first()
            
            if row:
                logging.info(f"Raw data from DB: {row}")
                logging.info(f"Raw is_admin value: {row[3]} (type: {type(row[3])})")
                
                # Создаем объект User с данными из запроса
                user = User()
                user.id = row[0]
                user.telegram_id = row[1]
                user.username = row[2]
                user.is_admin = row[3]
                user.media_outlet = row[4]
                
                logging.info(f"Created user object: id={user.id}, "
                           f"telegram_id={user.telegram_id}, "
                           f"is_admin={user.is_admin} (type: {type(user.is_admin)})")
            else:
                logging.warning(f"User not found: {user_id}")
                user = None
            
            data['user'] = user
            return await handler(event, data)
            
        except Exception as e:
            logging.error(f"Error in UserMiddleware: {e}", exc_info=True)
            raise 