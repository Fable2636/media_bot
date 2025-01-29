from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def get_admin_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Создать задание", callback_data="create_task"),
            InlineKeyboardButton(text="Просмотр публикаций", callback_data="review_posts")
        ],
        [
            InlineKeyboardButton(text="Экспорт отчётов", callback_data="export_reports")
        ]
    ])

def get_moderation_keyboard(submission_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Одобрить", callback_data=f"approve_submission_{submission_id}"),
            InlineKeyboardButton(text="На доработку", callback_data=f"revise_{submission_id}")
        ]
    ])