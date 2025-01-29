from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from src.services.user_service import UserService
from src.database.engine import AsyncSessionLocal

class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message | CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        async with AsyncSessionLocal() as session:
            user_service = UserService(session)
            
            user = await user_service.get_user_by_telegram_id(event.from_user.id)
            if not user:
                if isinstance(event, Message):
                    await event.answer("У вас нет доступа к боту.")
                else:
                    await event.message.answer("У вас нет доступа к боту.")
                return
            
            data["user"] = user
            data["session"] = session
            return await handler(event, data)