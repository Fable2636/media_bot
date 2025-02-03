from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from src.database.models.submission import SubmissionStatus

async def get_moderation_keyboard(submission_id: int) -> InlineKeyboardMarkup:
    """Возвращает клавиатуру для модерации публикации"""
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
    
    return InlineKeyboardMarkup(inline_keyboard=[buttons]) 