from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from src.states.task_states import TaskStates
from src.services.task_service import TaskService
from src.services.submission_service import SubmissionService
from src.keyboards.media_kb import get_media_main_keyboard, get_task_keyboard
from src.keyboards.moderation_kb import get_moderation_keyboard
from src.utils.logger import logger
from src.database.models import User, Submission
from src.database.models.submission import SubmissionStatus
from sqlalchemy.ext.asyncio import AsyncSession
import logging
from aiogram.exceptions import TelegramBadRequest
import re
from sqlalchemy import select

router = Router()

@router.callback_query(F.data == "active_tasks")
async def show_active_tasks(
    callback: CallbackQuery, 
    session: AsyncSession,
    user: User,
    bot: Bot
):
    try:
        task_service = TaskService(session)
        tasks = await task_service.get_active_tasks()
        
        logging.info(f"Received {len(tasks)} tasks")
        
        if not tasks:
            await callback.message.edit_text(
                "Нет активных заданий",
                reply_markup=get_media_main_keyboard()
            )
            await callback.answer()
            return
        
        # Удаляем предыдущее сообщение с заданиями
        await callback.message.delete()
        
        for task in tasks:
            logging.info(f"Processing task {task.id}, photo={task.photo}")
            
            # Проверяем, взято ли задание текущим пользователем
            assignment = await task_service.get_task_assignment(task.id, user.media_outlet)
            
            if assignment:
                # Если задание уже взято, показываем кнопку "Отправить текст"
                keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(
                        text="📝 Отправить текст",
                        callback_data=f"submit_task_{task.id}"
                    )
                ]])
            else:
                # Если задание не взято, показываем кнопку "Взять в работу"
                keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(
                        text="✅ Взять в работу",
                        callback_data=f"take_task_{task.id}"
                    )
                ]])
            
            if task.photo:  # Если есть фото, отправляем его
                try:
                    logging.info(f"Attempting to send photo for task {task.id}")
                    await bot.send_photo(
                        chat_id=callback.message.chat.id,
                        photo=task.photo,
                        caption=(
                            f"Задание #{task.id}\n"
                            f"Пресс-релиз: {task.press_release_link[:300] + '...' if len(task.press_release_link) > 300 else task.press_release_link}\n"
                            f"Дедлайн: {task.deadline.strftime('%d.%m.%Y %H:%M')}"
                        ),
                        reply_markup=keyboard
                    )
                    logging.info(f"Successfully sent photo for task {task.id}")
                except Exception as e:
                    logging.error(f"Error sending photo for task {task.id}: {str(e)}", exc_info=True)
                    await callback.message.answer(
                        f"Задание #{task.id}\n"
                        f"Пресс-релиз: {task.press_release_link[:300] + '...' if len(task.press_release_link) > 300 else task.press_release_link}\n"
                        f"Дедлайн: {task.deadline.strftime('%d.%m.%Y %H:%M')}",
                        reply_markup=keyboard
                    )
            else:  # Если фото нет, отправляем просто текст
                await callback.message.answer(
                    f"Задание #{task.id}\n"
                    f"Пресс-релиз: {task.press_release_link[:300] + '...' if len(task.press_release_link) > 300 else task.press_release_link}\n"
                    f"Дедлайн: {task.deadline.strftime('%d.%m.%Y %H:%M')}",
                    reply_markup=keyboard
                )
        
        await callback.answer()
        
    except Exception as e:
        logging.error(f"Error in show_active_tasks: {str(e)}", exc_info=True)
        await callback.answer("Произошла ошибка при загрузке заданий")

@router.callback_query(F.data.startswith("take_task_"))
async def take_task(
    callback: CallbackQuery, 
    session: AsyncSession,
    user: User,
    bot: Bot
):
    try:
        task_id = int(callback.data.split("_")[-1])
        
        task_service = TaskService(session)
        task = await task_service.get_task_by_id(task_id)
        
        if not task:
            await callback.answer("Задание не найдено")
            return
        
        # Проверяем, не взято ли задание уже другим представителем этого СМИ
        existing_assignment = await task_service.get_task_assignment(task_id, user.media_outlet)
        if existing_assignment:
            await callback.answer("Задание уже взято другим представителем вашего СМИ")
            return
            
        # Проверяем, нет ли уже одобренной публикации от этого СМИ
        has_completed_submission = await task_service.check_media_outlet_submission(task_id, user.media_outlet)
        if has_completed_submission:
            await callback.answer("Ваше СМИ уже выполнило это задание")
            return
        
        # Пытаемся назначить задание
        assignment = await task_service.assign_task(task_id, user.media_outlet)
        
        if not assignment:
            await callback.answer("Не удалось взять задание. Возможно, оно уже выполнено или взято в работу.")
            return
        
        # Отправляем уведомление пользователю с кнопкой "Отправить текст"
        await bot.send_message(
            user.telegram_id,
            f"✅ Вы взяли задание #{task_id} в работу\n"
            f"Пресс-релиз: {task.press_release_link[:300] + '...' if len(task.press_release_link) > 300 else task.press_release_link}\n"
            f"Дедлайн: {task.deadline.strftime('%d.%m.%Y %H:%M')}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text="📝 Отправить текст",
                    callback_data=f"submit_task_{task_id}"
                )
            ]])
        )
        
        await callback.answer("Задание успешно взято в работу")
        
    except Exception as e:
        logging.error(f"Error in take_task: {e}", exc_info=True)
        await callback.answer("Произошла ошибка при взятии задания")

@router.callback_query(F.data == "my_submissions")
async def show_user_submissions(
    callback: CallbackQuery, 
    session: AsyncSession,
    user: User
):
    submission_service = SubmissionService(session)
    
    # Получаем активные публикации
    active_submissions = await submission_service.get_user_submissions(user.id, active_only=True)
    
    # Получаем архивные публикации
    archive_submissions = await submission_service.get_user_submissions(user.id, active_only=False)
    
    if not active_submissions and not archive_submissions:
        await callback.message.answer("У вас пока нет публикаций")
        return
    
    # Отображаем активные публикации
    if active_submissions:
        await callback.message.answer("Активные публикации:")
        for submission in active_submissions:
            await show_submission_details(callback.message, submission)
    
    # Добавляем кнопку для просмотра архива
    if archive_submissions:
        await callback.message.answer(
            "Есть архивные публикации",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text="Показать архив",
                    callback_data="show_archive"
                )
            ]])
        )
    
    await callback.answer()

@router.message(Command("start"))
async def cmd_start(message: Message, user):
    await message.answer(
        "Добро пожаловать в систему управления публикациями!",
        reply_markup=get_media_main_keyboard()
    )

@router.callback_query(F.data.startswith("submit_task_"))
async def handle_submit_task(
    callback: CallbackQuery, 
    state: FSMContext,
    user: User,
    session: AsyncSession
):
    try:
        task_id = int(callback.data.split("_")[-1])
        
        # Проверяем, взято ли задание этим пользователем
        task_service = TaskService(session)
        assignment = await task_service.get_task_assignment(task_id, user.media_outlet)
        
        if not assignment:
            await callback.answer("Вы не можете отправить текст для этого задания", show_alert=True)
            return
        
        # Устанавливаем состояние ожидания текста
        await state.set_state(TaskStates.waiting_for_text)
        
        # Разрешаем отправку текста и убираем блокировку
        await state.set_data({
            'task_id': task_id,
            'can_send_text': True,
            'is_blocked': False
        })
        
        await callback.message.answer("❌ Пожалуйста, отправьте текст задания:")
        await callback.answer()
        
    except Exception as e:
        logging.error(f"Error in handle_submit_task: {e}", exc_info=True)
        await callback.answer("Произошла ошибка при обработке запроса", show_alert=True)

@router.callback_query(F.data.startswith("submit_revision_"))
async def handle_revision_request(
    callback: CallbackQuery, 
    state: FSMContext,
    session: AsyncSession
):
    try:
        submission_id = int(callback.data.split("_")[2])
        
        # Получаем публикацию
        submission_service = SubmissionService(session)
        submission = await submission_service.get_submission(submission_id)
        
        if not submission:
            await callback.answer("Публикация не найдена", show_alert=True)
            return
        
        # Определяем тип контента для доработки
        is_photo_revision = submission.previous_status == SubmissionStatus.TEXT_APPROVED.value
        
        # Сохраняем submission_id и task_id в состоянии
        await state.update_data(
            submission_id=submission_id,
            task_id=submission.task_id,  # Важно: сохраняем task_id из публикации
            is_photo_revision=is_photo_revision,
            can_send_text=True,  # Сразу разрешаем отправку текста
            is_blocked=False  # Убираем блокировку
        )
        
        # Переходим в соответствующее состояние
        if is_photo_revision:
            await state.set_state(TaskStates.waiting_for_photo)
            await callback.message.answer("❌ Пожалуйста, отправьте исправленное фото.")
        else:
            await state.set_state(TaskStates.waiting_for_text)
            await callback.message.answer("❌ Пожалуйста, отправьте исправленный текст задания:")
            
        await callback.answer()
        
    except Exception as e:
        logging.error(f"Error in handle_revision_request: {e}", exc_info=True)
        await callback.answer("Произошла ошибка при обработке запроса", show_alert=True)

@router.message(TaskStates.waiting_for_text)
async def handle_submission_text(
    message: Message, 
    state: FSMContext, 
    session: AsyncSession,
    user: User,
    bot: Bot
):
    try:
        # Проверяем, был ли переход по кнопке
        data = await state.get_data()
        submission_id = data.get('submission_id')
        task_id = data.get('task_id')
        
        # Если отправка заблокирована или не было нажатия кнопки
        if data.get('is_blocked') or not data.get('can_send_text', False):
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text="Отправить текст",
                    callback_data=f"send_text_{submission_id}" if submission_id else "send_text"
                )
            ]])
            await message.answer(
                "❌ Для отправки текста нажмите кнопку ниже:",
                reply_markup=keyboard
            )
            # Блокируем отправку и сохраняем данные
            await state.set_data({
                'task_id': task_id,
                'submission_id': submission_id,
                'can_send_text': False,
                'is_blocked': True
            })
            return

        # Проверяем длину текста
        if len(message.text) > 3500:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text="Отправить текст",
                    callback_data=f"send_text_{submission_id}" if submission_id else "send_text"
                )
            ]])
            await message.answer(
                "❌ Текст слишком длинный. Максимальная длина - 3500 символов.",
                reply_markup=keyboard
            )
            # Блокируем отправку и сохраняем данные
            await state.set_data({
                'task_id': task_id,
                'submission_id': submission_id,
                'can_send_text': False,
                'is_blocked': True
            })
            return
        
        submission_service = SubmissionService(session)
        
        if submission_id:
            # Проверяем статус публикации перед обновлением
            submission = await submission_service.get_submission(submission_id)
            if not submission:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(
                        text="Отправить текст",
                        callback_data=f"send_text_{submission_id}"
                    )
                ]])
                await message.answer(
                    "❌ Задание не найдено.",
                    reply_markup=keyboard
                )
                # Блокируем отправку и сохраняем данные
                await state.set_data({
                    'task_id': task_id,
                    'submission_id': submission_id,
                    'can_send_text': False,
                    'is_blocked': True
                })
                return
                
            if submission.status != SubmissionStatus.REVISION.value:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(
                        text="Отправить текст",
                        callback_data=f"send_text_{submission_id}"
                    )
                ]])
                await message.answer(
                    "❌ Нельзя отправить исправленный текст. Задание не находится на доработке.",
                    reply_markup=keyboard
                )
                # Блокируем отправку и сохраняем данные
                await state.set_data({
                    'task_id': task_id,
                    'submission_id': submission_id,
                    'can_send_text': False,
                    'is_blocked': True
                })
                return
                
            # Обновляем существующую публикацию
            submission = await submission_service.update_submission_content(
                submission_id=submission_id,
                content=message.text,
                photo=None  # Фото не меняем
            )
            action_text = "исправленный "
            task_id = submission.task_id  # Используем task_id из публикации
        else:
            # Проверяем, нет ли уже публикации для этого задания
            submissions = await submission_service.get_user_submissions(user.id, active_only=True)
            existing_submission = next((s for s in submissions if s.task_id == task_id), None)
            
            if existing_submission:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(
                        text="Отправить текст",
                        callback_data="send_text"
                    )
                ]])
                await message.answer(
                    "❌ У вас уже есть текст для этого задания. Нельзя создать больше одного текста.",
                    reply_markup=keyboard
                )
                # Блокируем отправку и сохраняем данные
                await state.set_data({
                    'task_id': task_id,
                    'submission_id': submission_id,
                    'can_send_text': False,
                    'is_blocked': True
                })
                return
                
            # Создаем новую публикацию
            if not task_id:
                logging.error("task_id is missing when creating submission")
                keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(
                        text="Отправить текст",
                        callback_data="send_text"
                    )
                ]])
                await message.answer(
                    "❌ Произошла ошибка при создании текста. Попробуйте снова.",
                    reply_markup=keyboard
                )
                await state.set_data({
                    'can_send_text': False,
                    'is_blocked': True
                })
                return

            # Проверяем существование задания
            task_service = TaskService(session)
            task = await task_service.get_task_by_id(task_id)
            
            if not task:
                logging.error(f"Task {task_id} not found when creating submission")
                keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(
                        text="Отправить текст",
                        callback_data="send_text"
                    )
                ]])
                await message.answer(
                    "❌ Задание не найдено. Попробуйте снова.",
                    reply_markup=keyboard
                )
                await state.set_data({
                    'can_send_text': False,
                    'is_blocked': True
                })
                return

            logging.info(f"Creating submission with task_id {task_id} for task {task}")
            submission = await submission_service.create_submission(
                task_id=task_id,
                user_id=user.id,
                content=message.text,
                photo=None
            )
            
            if not submission or not submission.task:
                logging.error(f"Failed to create submission for task {task_id} or task not loaded")
                keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(
                        text="Отправить текст",
                        callback_data="send_text"
                    )
                ]])
                await message.answer(
                    "❌ Не удалось создать текст. Попробуйте снова.",
                    reply_markup=keyboard
                )
                await state.set_data({
                    'task_id': task_id,
                    'can_send_text': False,
                    'is_blocked': True
                })
                return
                
            action_text = "новый "
        
        # Уведомляем админов о тексте
        from src.config.users import ADMINS
        for admin in ADMINS:
            try:
                notification_text = (
                    f"📨 {action_text}текст для задания #{submission.task_id}\n"
                    f"От: {user.media_outlet}\n"
                    f"ID пользователя: {user.telegram_id}\n"
                    f"Имя пользователя: @{user.username}\n"
                    f"Текст задания:\n{message.text}"
                )
                
                keyboard = await get_moderation_keyboard(submission.id)
                
                await bot.send_message(
                    admin["telegram_id"],
                    notification_text,
                    reply_markup=keyboard
                )
            except Exception as e:
                logging.error(f"Не удалось отправить уведомление администратору {admin['username']} (ID: {admin['telegram_id']}): {e}")
        
        await message.answer(
            f"✅ {action_text}текст успешно отправлен на проверку. Ожидайте одобрения.",
            reply_markup=get_media_main_keyboard()
        )
        
        # Полностью очищаем состояние после успешной отправки
        await state.clear()
        
    except Exception as e:
        logging.error(f"Error in handle_submission_text: {e}", exc_info=True)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text="Отправить текст",
                callback_data=f"send_text_{data.get('submission_id')}" if data.get('submission_id') else "send_text"
            )
        ]])
        await message.answer(
            "❌ Произошла ошибка при отправке текста. Попробуйте снова.",
            reply_markup=keyboard
        )
        # Блокируем отправку и сохраняем данные
        await state.set_data({
            'task_id': data.get('task_id'),
            'submission_id': data.get('submission_id'),
            'can_send_text': False,
            'is_blocked': True
        })

@router.callback_query(F.data.startswith("approve_submission_"))
async def approve_submission(callback: CallbackQuery, session: AsyncSession, bot: Bot):
    submission_id = int(callback.data.split("_")[-1])
    submission_service = SubmissionService(session)

    try:
        # Получаем публикацию с данными пользователя
        submission = await submission_service.get_submission_with_user(submission_id)
        logging.info(f"Processing approval for submission {submission_id}")
        logging.info(f"Initial status: {submission.status}, Has photo: {bool(submission.photo)}")
        
        # Одобряем публикацию
        submission = await submission_service.approve_submission(submission_id)
        logging.info(f"After approval status: {submission.status}")
        
        # Обновляем сообщение админа
        message_text = callback.message.text or callback.message.caption
        if message_text:
            status_text = "✅ Текст одобрен" if submission.status == SubmissionStatus.TEXT_APPROVED.value else "✅ Задание полностью одобрено"
            message_text = message_text.split("\nСтатус:")[0] + f"\nСтатус: {status_text}"
            
            try:
                if callback.message.photo:
                    await callback.message.edit_caption(
                        caption=message_text,
                        reply_markup=callback.message.reply_markup
                    )
                else:
                    await callback.message.edit_text(
                        text=message_text,
                        reply_markup=callback.message.reply_markup
                    )
            except Exception as e:
                logging.error(f"Error updating admin message: {e}")

        # Отправляем только уведомление через send_user_notification
        await send_user_notification(bot, submission)
        
        # Отправляем ответ на callback
        if submission.status == SubmissionStatus.TEXT_APPROVED.value:
            await callback.answer("Текст одобрен. Ожидаем фото от пользователя.")
        elif submission.status == SubmissionStatus.APPROVED.value:
            await callback.answer("Задание полностью одобрено.")
        
    except Exception as e:
        logging.error(f"Error approving submission: {e}", exc_info=True)
        await callback.answer("Произошла ошибка при одобрении задания")

@router.callback_query(F.data.startswith("attach_photo_"))
async def handle_attach_photo(callback: CallbackQuery, state: FSMContext):
    try:
        submission_id = int(callback.data.split("_")[-1])
        
        # Сохраняем ID публикации в состоянии
        await state.update_data(
            submission_id=submission_id,
            can_send_photo=False,  # Изначально блокируем отправку фото
            is_blocked=True
        )
        
        # Переводим пользователя в состояние ожидания фото
        await state.set_state(TaskStates.waiting_for_photo)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text="📎 Отправить фото",
                callback_data="send_photo"
            )
        ]])
        
        await callback.message.answer(
            "❌ Для отправки фото нажмите кнопку ниже:",
            reply_markup=keyboard
        )
        await callback.answer()
        
    except Exception as e:
        logging.error(f"Error in handle_attach_photo: {e}", exc_info=True)
        await callback.answer("Произошла ошибка при обработке запроса", show_alert=True)

@router.callback_query(F.data == "send_photo")
async def prompt_for_photo(callback: CallbackQuery, state: FSMContext):
    try:
        # Сохраняем текущие данные из состояния
        current_data = await state.get_data()
        
        # Обновляем состояние, сохраняя все предыдущие данные и разрешая отправку фото
        await state.set_data({
            **current_data,
            'can_send_photo': True,
            'is_blocked': False
        })
        
        await callback.message.edit_text(
            "❌ Пожалуйста, отправьте фото:",
            reply_markup=None
        )
        await callback.answer()
        
    except Exception as e:
        logging.error(f"Error in prompt_for_photo: {e}", exc_info=True)
        await callback.answer("Произошла ошибка при обработке запроса", show_alert=True)

@router.message(TaskStates.waiting_for_photo)
async def handle_photo_submission(
    message: Message, 
    state: FSMContext, 
    session: AsyncSession,
    bot: Bot
):
    try:
        data = await state.get_data()
        
        # Если отправка заблокирована или не было нажатия кнопки
        if data.get('is_blocked') or not data.get('can_send_photo', False):
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text="📎 Отправить фото",
                    callback_data="send_photo"
                )
            ]])
            await message.answer(
                "❌ Для отправки фото нажмите кнопку ниже:",
                reply_markup=keyboard
            )
            return
            
        if not message.photo:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text="📎 Отправить фото",
                    callback_data="send_photo"
                )
            ]])
            await message.answer(
                "❌ Пожалуйста, отправьте фото, а не другой тип сообщения.",
                reply_markup=keyboard
            )
            return

        submission_id = data.get('submission_id')
        
        if not submission_id:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text="📎 Отправить фото",
                    callback_data="send_photo"
                )
            ]])
            await message.answer(
                "❌ Произошла ошибка. Попробуйте снова.",
                reply_markup=keyboard
            )
            await state.clear()
            return
        
        # Проверяем статус публикации перед обновлением
        submission_service = SubmissionService(session)
        submission = await submission_service.get_submission(submission_id)
        
        # Разрешаем отправку фото если:
        # 1. Публикация на доработке (REVISION)
        # 2. Текст уже одобрен (TEXT_APPROVED)
        if not submission or (
            submission.status != SubmissionStatus.REVISION.value and 
            submission.status != SubmissionStatus.TEXT_APPROVED.value
        ):
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text="📎 Отправить фото",
                    callback_data="send_photo"
                )
            ]])
            await message.answer(
                "❌ Нельзя отправить фото. Дождитесь одобрения текста или отправки на доработку.",
                reply_markup=keyboard
            )
            await state.clear()
            return

        # Получаем файл_id самой большой версии фото
        photo = message.photo[-1].file_id
        
        # Обновляем публикацию
        submission = await submission_service.update_submission_content(
            submission_id=submission_id,
            photo=photo
        )
        
        # Получаем обновленную публикацию с данными пользователя
        submission = await submission_service.get_submission_with_user(submission_id)
        
        # Подготавливаем превью текста (первые 300 символов)
        text_preview = submission.content[:300]
        if len(submission.content) > 300:
            text_preview += "..."
        
        # Уведомляем админов о новом фото
        from src.config.users import ADMINS
        for admin in ADMINS:
            try:
                await bot.send_photo(
                    chat_id=admin["telegram_id"],
                    photo=photo,
                    caption=(
                        f"📸 {'Исправленное' if submission.status == SubmissionStatus.REVISION.value else 'Новое'} фото для задания #{submission.task_id}\n"
                        f"От: {submission.user.media_outlet}\n"
                        f"ID пользователя: {submission.user.telegram_id}\n"
                        f"Имя пользователя: @{submission.user.username}\n\n"
                        f"Текст задания:\n{text_preview}"
                    ),
                    reply_markup=await get_moderation_keyboard(submission.id)
                )
            except Exception as e:
                logging.error(f"Не удалось отправить уведомление администратору {admin['username']} (ID: {admin['telegram_id']}): {e}")
        
        # Отправляем уведомление пользователю
        await send_user_notification(bot, submission)
        
        await message.answer(
            "✅ Фото успешно добавлено к заданию. Ожидайте одобрения.",
            reply_markup=get_media_main_keyboard()
        )
        await state.clear()
        
    except Exception as e:
        logging.error(f"Error in handle_photo_submission: {e}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при сохранении фото",
            reply_markup=get_media_main_keyboard()
        )
        await state.clear()

@router.callback_query(F.data == "show_archive")
async def show_archive(
    callback: CallbackQuery, 
    session: AsyncSession,
    user: User
):
    submission_service = SubmissionService(session)
    archive_submissions = await submission_service.get_user_submissions(user.id, active_only=False)
    
    if not archive_submissions:
        await callback.answer("Архив пуст")
        return
    
    await callback.message.answer("Архивные публикации:")
    for submission in archive_submissions:
        await show_submission_details(callback.message, submission)
    
    await callback.answer()

async def show_submission_details(message: Message, submission: Submission):
    status_text = {
        SubmissionStatus.PENDING.value: '🕒 Текст на проверке',
        SubmissionStatus.TEXT_APPROVED.value: '✅ Текст одобрен, ожидается фото',
        SubmissionStatus.PHOTO_PENDING.value: '🕒 Фото на проверке',
        SubmissionStatus.APPROVED.value: '✅ Задание одобрено',
        SubmissionStatus.REVISION.value: '📝 Требует доработки',
        SubmissionStatus.COMPLETED.value: '✅ Опубликовано'
    }.get(submission.status, submission.status)
    
    text = (
        f"Задание #{submission.task_id}\n"
        f"Статус: {status_text}\n"
        f"Дата отправки: {submission.submitted_at.strftime('%d.%m.%Y %H:%M')}\n"
    )
    
    if submission.revision_comment:
        text += f"Комментарий: {submission.revision_comment}\n"
    
    if submission.published_link:
        text += f"Ссылка на публикацию: {submission.published_link}\n"
    
    keyboard = None
    if submission.status == SubmissionStatus.REVISION.value:
        # Определяем, что нужно доработать на основе previous_status
        is_photo_revision = submission.previous_status == SubmissionStatus.TEXT_APPROVED.value
        if is_photo_revision:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text="Отправить исправленное фото",
                    callback_data=f"submit_revision_{submission.id}"
                )
            ]])
        else:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text="Отправить исправленный текст",
                    callback_data=f"submit_revision_{submission.id}"
                )
            ]])
    elif submission.status == SubmissionStatus.TEXT_APPROVED.value:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text="Прикрепить фото",
                callback_data=f"attach_photo_{submission.id}"
            )
        ]])
    elif submission.status == SubmissionStatus.APPROVED.value:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text="Отправить ссылку",
                callback_data=f"send_link_{submission.id}"
            )
        ]])
    
    if submission.photo:
        await message.answer_photo(
            photo=submission.photo,
            caption=text,
            reply_markup=keyboard
        )
    else:
        await message.answer(text, reply_markup=keyboard)

@router.message(F.text == "Архив")
async def handle_archive_button(
    message: Message, 
    session: AsyncSession,
    user: User
):
    submission_service = SubmissionService(session)
    archive_submissions = await submission_service.get_user_submissions(user.id, active_only=False)
    
    if not archive_submissions:
        await message.answer("Архив пуст")
        return
    
    await message.answer("Архивные публикации:")
    for submission in archive_submissions:
        await show_submission_details(message, submission)

@router.callback_query(F.data.startswith("send_link_"))
async def handle_send_link_button(callback: CallbackQuery, state: FSMContext):
    submission_id = int(callback.data.split("_")[-1])
    await state.update_data(submission_id=submission_id)
    await state.set_state(TaskStates.waiting_for_link)
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="Отправить ссылку",
            callback_data="send_text"
        )
    ]])
    await callback.message.answer(
        "❌ Для отправки ссылки нажмите кнопку ниже:",
        reply_markup=keyboard
    )
    await callback.answer()

@router.message(TaskStates.waiting_for_link)
async def handle_link_submission(
    message: Message, 
    state: FSMContext, 
    session: AsyncSession,
    bot: Bot
):
    try:
        # Проверяем, был ли переход по кнопке
        data = await state.get_data()
        if not data.get('can_send_text', False):  # Явно указываем False как значение по умолчанию
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text="Отправить ссылку",
                    callback_data="send_text"
                )
            ]])
            await message.answer(
                "❌ Для отправки ссылки нажмите кнопку ниже:",
                reply_markup=keyboard
            )
            # Очищаем состояние, сохраняя только необходимые данные
            await state.set_data({
                'submission_id': data.get('submission_id'),
                'can_send_text': False
            })
            return  # Важно: ранний возврат, чтобы предотвратить дальнейшее выполнение

        # Проверяем длину ссылки только если разрешена отправка
        if len(message.text) > 3500:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text="Отправить ссылку",
                    callback_data="send_text"
                )
            ]])
            await message.answer(
                "❌ Ссылка слишком длинная. Максимальная длина - 3500 символов.",
                reply_markup=keyboard
            )
            # Сбрасываем флаг can_send_text
            await state.set_data({
                'submission_id': data.get('submission_id'),
                'can_send_text': False
            })
            return  # Важно: ранний возврат после ошибки
            
        data = await state.get_data()
        submission_id = data.get('submission_id')
        
        if not submission_id:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text="Отправить ссылку",
                    callback_data="send_text"
                )
            ]])
            await message.answer(
                "❌ Произошла ошибка. Попробуйте снова.",
                reply_markup=keyboard
            )
            await state.clear()
            return
        
        submission_service = SubmissionService(session)
        submission = await submission_service.get_submission(submission_id)
        
        if not submission:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text="Отправить ссылку",
                    callback_data="send_text"
                )
            ]])
            await message.answer(
                "❌ Задание не найдено.",
                reply_markup=keyboard
            )
            await state.clear()
            return

        # Проверяем, нет ли уже ссылки у этой публикации
        if submission.published_link:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text="Отправить ссылку",
                    callback_data="send_text"
                )
            ]])
            await message.answer(
                "❌ Вы уже отправляли ссылку для этого задания. Повторная отправка невозможна.",
                reply_markup=keyboard
            )
            await state.clear()
            return

        if submission.status != SubmissionStatus.APPROVED.value:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text="Отправить ссылку",
                    callback_data="send_text"
                )
            ]])
            await message.answer(
                "❌ Нельзя отправить ссылку, пока задание не одобрено полностью.",
                reply_markup=keyboard
            )
            await state.clear()
            return
        
        # Сохраняем ссылку
        submission = await submission_service.add_published_link(
            submission_id=submission_id,
            published_link=message.text
        )
        
        # Уведомляем админов
        from src.config.users import ADMINS
        for admin in ADMINS:
            try:
                await bot.send_message(
                    admin["telegram_id"],
                    f"ℹ️ Информация о задании\n"
                    f"Пользователь @{message.from_user.username} отправил ссылку на задание #{submission.task_id}:\n"
                    f"{message.text}"
                )
            except Exception as e:
                logging.error(f"Не удалось отправить уведомление администратору {admin['username']}: {e}")
        
        await message.answer(
            "✅ Ссылка успешно добавлена. Спасибо!",
            reply_markup=get_media_main_keyboard()
        )
        # Очищаем состояние, сохраняя только необходимые данные
        await state.set_data({
            'submission_id': submission.id,
            'can_send_text': False
        })
        
    except Exception as e:
        logging.error(f"Error in handle_link_submission: {e}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при добавлении ссылки",
            reply_markup=get_media_main_keyboard()
        )
        # Очищаем состояние при ошибке
        await state.set_data({
            'submission_id': data.get('submission_id'),
            'can_send_text': False
        })

async def send_user_notification(bot: Bot, submission: Submission):
    """Отправляет уведомление пользователю о статусе публикации"""
    try:
        if not submission.user or not submission.user.telegram_id:
            logging.error(f"No user or telegram_id found for submission {submission.id}")
            return
            
        if submission.status == SubmissionStatus.TEXT_APPROVED.value:
            # Если текст одобрен, отправляем сообщение с кнопкой для фото
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text="📎 Прикрепить фото",
                    callback_data=f"attach_photo_{submission.id}"
                )
            ]])
            await bot.send_message(
                chat_id=submission.user.telegram_id,
                text=f"✅ Ваш текст для задания #{submission.task_id} одобрен!\nТеперь необходимо прикрепить фото к публикации.",
                reply_markup=keyboard
            )
        elif submission.status == SubmissionStatus.APPROVED.value:
            # Если публикация полностью одобрена
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text="🔗 Отправить ссылку",
                    callback_data=f"send_link_{submission.id}"
                )
            ]])
            await bot.send_message(
                chat_id=submission.user.telegram_id,
                text=f"✅ Ваша публикация для задания #{submission.task_id} полностью одобрена!\nТеперь отправьте ссылку на опубликованный материал.",
                reply_markup=keyboard
            )
        elif submission.status == SubmissionStatus.COMPLETED.value:
            # Если публикация завершена
            await bot.send_message(
                chat_id=submission.user.telegram_id,
                text=f"✅ Ваша публикация для задания #{submission.task_id} успешно завершена! Спасибо за сотрудничество.",
                reply_markup=get_media_main_keyboard()
            )
    except Exception as e:
        logging.error(f"Error in send_user_notification: {e}", exc_info=True)

@router.message(F.text == "Активные задания")
async def handle_active_tasks_button(
    message: Message, 
    session: AsyncSession,
    user: User,
    bot: Bot
):
    try:
        task_service = TaskService(session)
        tasks = await task_service.get_active_tasks(user.media_outlet)
        
        if not tasks:
            await message.answer("У вас нет активных заданий")
            return
            
        logging.info(f"Received {len(tasks)} tasks")
        
        # Отправляем каждое задание отдельным сообщением
        for task in tasks:
            try:
                logging.info(f"Processing task {task.id}, photo={task.photo}")
                
                # Проверяем, взято ли задание в работу
                assignment = await task_service.get_task_assignment(task.id, user.media_outlet)
                status_text = "✅ В работе" if assignment else "🆕 Доступно"
                
                # Обрезаем ссылку если она слишком длинная
                press_release_link = task.press_release_link
                if len(press_release_link) > 300:
                    press_release_link = press_release_link[:297] + "..."
                
                # Формируем текст для задания
                task_text = (
                    f"Задание #{task.id}\n"
                    f"Статус: {status_text}\n"
                    f"Дедлайн: {task.deadline.strftime('%d.%m.%Y %H:%M')}\n"
                    f"Пресс-релиз: {press_release_link}"
                )
                
                # Формируем клавиатуру в зависимости от статуса
                keyboard = None
                if assignment:
                    # Если задание в работе, показываем кнопку "Отправить текст"
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                        InlineKeyboardButton(
                            text="📝 Отправить текст",
                            callback_data=f"submit_task_{task.id}"
                        )
                    ]])
                else:
                    # Если задание не взято, показываем кнопку "Взять в работу"
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                        InlineKeyboardButton(
                            text="✅ Взять в работу",
                            callback_data=f"take_task_{task.id}"
                        )
                    ]])
                
                # Если есть фото, отправляем с фото
                if task.photo:
                    await message.answer_photo(
                        photo=task.photo,
                        caption=task_text,
                        reply_markup=keyboard
                    )
                else:
                    # Иначе отправляем просто текст
                    await message.answer(
                        task_text,
                        reply_markup=keyboard
                    )
            except Exception as e:
                logging.error(f"Error processing task {task.id}: {e}", exc_info=True)
                continue  # Продолжаем с следующим заданием даже если текущее вызвало ошибку
                
    except Exception as e:
        logging.error(f"Error in show_active_tasks: {e}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при получении списка заданий",
            reply_markup=get_media_main_keyboard()
        )

@router.message(F.text == "Мои публикации")
async def handle_my_submissions_button(
    message: Message, 
    session: AsyncSession,
    user: User
):
    submission_service = SubmissionService(session)
    
    # Получаем активные публикации
    active_submissions = await submission_service.get_user_submissions(user.id, active_only=True)
    
    # Получаем архивные публикации
    archive_submissions = await submission_service.get_user_submissions(user.id, active_only=False)
    
    if not active_submissions and not archive_submissions:
        await message.answer("У вас пока нет публикаций")
        return
    
    # Отображаем активные публикации
    if active_submissions:
        await message.answer("Активные публикации:")
        for submission in active_submissions:
            await show_submission_details(message, submission)
    
    # Добавляем кнопку для просмотра архива
    if archive_submissions:
        await message.answer(
            "Есть архивные публикации",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text="Показать архив",
                    callback_data="show_archive"
                )
            ]])
        )

@router.callback_query(F.data.startswith("send_text_"))
async def prompt_for_text(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    try:
        # Получаем submission_id из callback_data
        submission_id = int(callback.data.split("_")[-1])
        
        # Получаем публикацию для получения task_id
        submission_service = SubmissionService(session)
        submission = await submission_service.get_submission(submission_id)
        
        if not submission:
            await callback.answer("Публикация не найдена", show_alert=True)
            return
        
        # Устанавливаем состояние ожидания текста
        await state.set_state(TaskStates.waiting_for_text)
        
        # Разрешаем отправку текста и убираем блокировку
        await state.set_data({
            'submission_id': submission_id,
            'task_id': submission.task_id,  # Сохраняем task_id из публикации
            'can_send_text': True,
            'is_blocked': False
        })
        
        await callback.message.answer("❌ Пожалуйста, отправьте исправленный текст задания:")
        await callback.answer()
        
    except Exception as e:
        logging.error(f"Error in prompt_for_text: {e}", exc_info=True)
        await callback.answer("Произошла ошибка при обработке запроса", show_alert=True)

@router.message(TaskStates.waiting_for_revision)
async def handle_revision_comment(
    message: Message, 
    state: FSMContext, 
    session: AsyncSession,
    bot: Bot
):
    try:
        # Проверяем, был ли переход по кнопке
        data = await state.get_data()
        if not data.get('can_send_text', False):  # Явно указываем False как значение по умолчанию
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text="Отправить комментарий",
                    callback_data="send_text"
                )
            ]])
            await message.answer(
                "❌ Для отправки комментария нажмите кнопку ниже:",
                reply_markup=keyboard
            )
            # Очищаем состояние, сохраняя только необходимые данные
            await state.set_data({
                'submission_id': data.get('submission_id'),
                'is_photo_revision': data.get('is_photo_revision'),
                'can_send_text': False
            })
            return  # Важно: ранний возврат, чтобы предотвратить дальнейшее выполнение

        # Проверяем длину комментария только если разрешена отправка
        if len(message.text) > 3500:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text="Отправить комментарий",
                    callback_data="send_text"
                )
            ]])
            await message.answer(
                "❌ Комментарий слишком длинный. Максимальная длина - 3500 символов.",
                reply_markup=keyboard
            )
            # Сбрасываем флаг can_send_text
            await state.set_data({
                'submission_id': data.get('submission_id'),
                'is_photo_revision': data.get('is_photo_revision'),
                'can_send_text': False
            })
            return  # Важно: ранний возврат после ошибки
            
        data = await state.get_data()
        submission_id = data.get('submission_id')
        is_photo_revision = data.get('is_photo_revision', False)
        
        if not submission_id:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text="Отправить комментарий",
                    callback_data="send_text"
                )
            ]])
            await message.answer(
                "❌ Произошла ошибка. Попробуйте снова.",
                reply_markup=keyboard
            )
            await state.clear()
            return

        submission_service = SubmissionService(session)
        submission = await submission_service.get_submission(submission_id)
        
        if not submission:
            await message.answer(
                "❌ Задание не найдено.",
                reply_markup=get_media_main_keyboard()
            )
            await state.clear()
            return

        # Сохраняем комментарий
        submission = await submission_service.add_revision_comment(
            submission_id=submission_id,
            comment=message.text
        )
        
        # Уведомляем админов
        from src.config.users import ADMINS
        for admin in ADMINS:
            try:
                await bot.send_message(
                    admin["telegram_id"],
                    f"📨 Добавлен комментарий к заданию #{submission.task_id}\n"
                    f"От: {submission.user.media_outlet}\n"
                    f"ID пользователя: {submission.user.telegram_id}\n"
                    f"Имя пользователя: @{submission.user.username}\n\n"
                    f"Комментарий:\n{message.text}"
                )
            except Exception as e:
                logging.error(f"Не удалось отправить уведомление администратору {admin['username']}: {e}")
        
        await message.answer(
            "✅ Комментарий успешно добавлен. Спасибо!",
            reply_markup=get_media_main_keyboard()
        )
        # Очищаем состояние, сохраняя только необходимые данные
        await state.set_data({
            'submission_id': submission.id,
            'is_photo_revision': data.get('is_photo_revision'),
            'can_send_text': False
        })
        
    except Exception as e:
        logging.error(f"Error in handle_revision_comment: {e}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при добавлении комментария",
            reply_markup=get_media_main_keyboard()
        )
        # Очищаем состояние при ошибке
        await state.set_data({
            'submission_id': data.get('submission_id'),
            'is_photo_revision': data.get('is_photo_revision'),
            'can_send_text': False
        })

@router.callback_query(F.data == "send_text")
async def prompt_for_new_text(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    try:
        logging.info("Starting prompt_for_new_text handler")
        
        # Получаем текущие данные из состояния
        data = await state.get_data()
        task_id = data.get('task_id')
        submission_id = data.get('submission_id')
        logging.info(f"Task ID from state: {task_id}, Submission ID: {submission_id}")
        
        # Если есть submission_id, получаем публикацию
        if submission_id:
            submission_service = SubmissionService(session)
            submission = await submission_service.get_submission(submission_id)
            if submission:
                task_id = submission.task_id
                logging.info(f"Found submission {submission_id} with task_id {task_id}")
        
        # Если task_id всё ещё нет, пытаемся получить его из текста сообщения
        if not task_id:
            message_text = callback.message.text or callback.message.caption
            logging.info(f"Message text: {message_text}")
            
            if message_text:
                task_patterns = [
                    r'Задание #(\d+)',
                    r'задание #(\d+)',
                    r'задания #(\d+)',
                    r'#(\d+)'
                ]
                
                for pattern in task_patterns:
                    task_match = re.search(pattern, message_text, re.IGNORECASE)
                    if task_match:
                        task_id = int(task_match.group(1))
                        logging.info(f"Found task_id {task_id} using pattern {pattern}")
                        break
        
        if not task_id:
            logging.error("Failed to extract task_id from any source")
            await callback.answer("Ошибка: не удалось определить ID задания", show_alert=True)
            return
            
        # Получаем пользователя
        user_query = select(User).where(User.telegram_id == callback.from_user.id)
        user_result = await session.execute(user_query)
        user = user_result.scalar_one_or_none()
        
        if not user:
            logging.error(f"User not found for telegram_id {callback.from_user.id}")
            await callback.answer("Ошибка: пользователь не найден", show_alert=True)
            return
            
        # Проверяем существование задания в базе данных
        task_service = TaskService(session)
        task = await task_service.get_task_by_id(task_id)
        
        if not task:
            logging.error(f"Task {task_id} not found in database")
            await callback.answer("Ошибка: задание не найдено в базе данных", show_alert=True)
            return
            
        logging.info(f"Found task in database: {task.id}")
        
        # Проверяем, взято ли задание этим СМИ
        assignment = await task_service.get_task_assignment(task_id, user.media_outlet)
        if not assignment and not submission_id:  # Пропускаем проверку если это исправление существующей публикации
            logging.error(f"Media outlet {user.media_outlet} has not taken task {task_id}")
            await callback.answer("Вы не можете отправить текст для этого задания. Сначала возьмите его в работу.", show_alert=True)
            return
        
        # Устанавливаем состояние ожидания текста
        await state.set_state(TaskStates.waiting_for_text)
        
        # Сохраняем данные в состоянии
        state_data = {
            'task_id': task_id,
            'submission_id': submission_id,  # Сохраняем submission_id если он есть
            'can_send_text': True,
            'is_blocked': False
        }
        await state.set_data(state_data)
        logging.info(f"State data set: {state_data}")
        
        await callback.message.edit_text("Пожалуйста, отправьте текст задания:")
        await callback.answer()
        
    except Exception as e:
        logging.error(f"Error in prompt_for_new_text: {e}", exc_info=True)
        await callback.answer("Произошла ошибка при обработке запроса", show_alert=True)
