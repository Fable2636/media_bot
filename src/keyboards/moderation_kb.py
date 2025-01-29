from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_moderation_keyboard(submission_id: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру для модерации публикации"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve_submission_{submission_id}"),
            InlineKeyboardButton(text="📝 На доработку", callback_data=f"revise_{submission_id}")
        ]
    ]) 