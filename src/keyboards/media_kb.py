from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def get_media_main_keyboard() -> ReplyKeyboardMarkup:
    """Создает основную клавиатуру для представителей СМИ"""
    keyboard = [
        [
            KeyboardButton(text="Активные задания"),
            KeyboardButton(text="Мои публикации")
        ],
        [
            KeyboardButton(text="Архив")
        ]
    ]
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_task_keyboard(task_id: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру для работы с заданием"""
    keyboard = [
        [
            InlineKeyboardButton(
                text="Взять в работу",
                callback_data=f"take_task_{task_id}"
            )
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)