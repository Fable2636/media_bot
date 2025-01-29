from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_start_keyboard() -> ReplyKeyboardMarkup:
    """Создает стартовую клавиатуру"""
    keyboard = [
        [KeyboardButton(text="Активные задания")],
        [KeyboardButton(text="Мои публикации")]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True) 