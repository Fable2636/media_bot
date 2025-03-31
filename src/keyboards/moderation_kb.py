from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from src.database.models.submission import SubmissionStatus
import logging

async def get_moderation_keyboard(submission_id: int) -> InlineKeyboardMarkup:
    """Возвращает клавиатуру для модерации публикации"""
    logging.info(f"Создание клавиатуры модерации для submission_id={submission_id}")
    buttons = []
    
    # Кнопка одобрения
    buttons.append(
        InlineKeyboardButton(
            text="✅ Одобрить",
            callback_data=f"approve_submission_{submission_id}"
        )
    )
    
    # Кнопка запроса доработки
    buttons.append(
        InlineKeyboardButton(
            text="📝 На доработку",
            callback_data=f"request_revision_{submission_id}"
        )
    )
    
    # Кнопка запроса ссылки
    buttons.append(
        InlineKeyboardButton(
            text="🔗 Запросить ссылку",
            callback_data=f"request_link_{submission_id}"
        )
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[buttons])
    # Используем безопасное логирование без вывода эмодзи
    logging.info(f"Клавиатура модерации создана для submission_id={submission_id}")
    return keyboard 