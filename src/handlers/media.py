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
from sqlalchemy.ext.asyncio import AsyncSession
import logging
from aiogram.exceptions import TelegramBadRequest

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
                        text="Отправить текст",
                        callback_data=f"submit_task_{task.id}"
                    )
                ]])
            else:
                # Если задание не взято, показываем кнопку "Взять в работу"
                keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(
                        text="Взять в работу",
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
                            f"Пресс-релиз: {task.press_release_link}\n"
                            f"Дедлайн: {task.deadline.strftime('%d.%m.%Y %H:%M')}"
                        ),
                        reply_markup=keyboard
                    )
                    logging.info(f"Successfully sent photo for task {task.id}")
                except Exception as e:
                    logging.error(f"Error sending photo for task {task.id}: {str(e)}", exc_info=True)
                    await callback.message.answer(
                        f"Задание #{task.id}\n"
                        f"Пресс-релиз: {task.press_release_link}\n"
                        f"Дедлайн: {task.deadline.strftime('%d.%m.%Y %H:%M')}",
                        reply_markup=keyboard
                    )
            else:  # Если фото нет, отправляем просто текст
                await callback.message.answer(
                    f"Задание #{task.id}\n"
                    f"Пресс-релиз: {task.press_release_link}\n"
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
        
        # Пытаемся назначить задание
        assignment = await task_service.assign_task(task_id, user.media_outlet)
        
        if not assignment:
            await callback.answer("Задание уже взято другим представителем вашего СМИ")
            return
        
        # Отправляем уведомление пользователю с кнопкой "Отправить текст"
        await bot.send_message(
            user.telegram_id,
            f"✅ Вы взяли задание #{task_id} в работу\n"
            f"Пресс-релиз: {task.press_release_link}\n"
            f"Дедлайн: {task.deadline.strftime('%d.%m.%Y %H:%M')}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text="Отправить текст",
                    callback_data=f"submit_task_{task_id}"
                )
            ]])
        )
        
        await callback.answer("Задание успешно взято в работу")
        
    except Exception as e:
        logging.error(f"Error in take_task: {e}", exc_info=True)
        await callback.answer("Произошла ошибка при взятии задания")

@router.message(TaskStates.waiting_for_submission)
async def handle_submission(
    message: Message, 
    state: FSMContext, 
    session: AsyncSession,
    user: User,
    bot: Bot
):
    try:
        if not message.photo:
            await message.answer("Пожалуйста, прикрепите фото к публикации.")
            return
        
        # Получаем данные из состояния
        data = await state.get_data()
        submission_id = data.get('submission_id')
        
        # Сохраняем фото и переходим в состояние ожидания текста
        photo = message.photo[-1].file_id
        await state.update_data(photo=photo)
        await state.set_state(TaskStates.waiting_for_text)
        await message.answer("Пожалуйста, отправьте текст публикации:")
        
    except Exception as e:
        logging.error(f"Error in handle_submission: {e}", exc_info=True)
        await message.answer(
            "Произошла ошибка при отправке публикации",
            reply_markup=get_media_main_keyboard()
        )
        await state.clear()

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
        
        # Сохраняем ID задания в состоянии
        await state.update_data(task_id=task_id)
        
        # Переводим пользователя в состояние ожидания фото
        await state.set_state(TaskStates.waiting_for_submission)
        
        await callback.message.answer(
            "Пожалуйста, прикрепите фото к публикации.",
            reply_markup=ReplyKeyboardRemove()
        )
        await callback.answer()
        
    except Exception as e:
        logging.error(f"Error in handle_submit_task: {e}", exc_info=True)
        await callback.answer("Произошла ошибка при обработке запроса")

@router.callback_query(F.data.startswith("submit_revision_"))
async def handle_revision_request(
    callback: CallbackQuery, 
    state: FSMContext,
    session: AsyncSession
):
    try:
        submission_id = int(callback.data.split("_")[2])
        
        # Получаем задание, связанное с этой публикацией
        submission_service = SubmissionService(session)
        submission = await submission_service.get_submission(submission_id)
        
        if not submission:
            await callback.answer("Публикация не найдена", show_alert=True)
            return
        
        # Сохраняем submission_id и task_id в состоянии
        await state.update_data(
            submission_id=submission_id,
            task_id=submission.task_id
        )
        
        # Переходим сразу в состояние ожидания фото
        await state.set_state(TaskStates.waiting_for_submission)
        
        await callback.message.answer("Пожалуйста, прикрепите фото к публикации.")
        await callback.answer()
        
    except Exception as e:
        logging.error(f"Error in handle_revision_request: {e}", exc_info=True)
        await callback.answer("Произошла ошибка при обработке запроса", show_alert=True)

@router.callback_query(F.data.startswith("send_link_"))
async def request_published_link(callback: CallbackQuery, state: FSMContext):
    submission_id = int(callback.data.split("_")[2])
    
    await state.set_state(TaskStates.waiting_for_link)
    await state.update_data(submission_id=submission_id)
    
    await callback.message.answer(
        "Пожалуйста, отправьте ссылку на опубликованный материал:"
    )
    await callback.answer()

@router.message(TaskStates.waiting_for_link)
async def handle_published_link(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    submission_id = data['submission_id']
    
    submission_service = SubmissionService(session)
    await submission_service.add_published_link(submission_id, message.text)
    
    await message.answer(
        "✅ Спасибо! Ссылка на публикацию добавлена.\n"
        "Задание выполнено."
    )
    await state.clear()

@router.message(Command("tasks"))
async def cmd_tasks(message: Message, session: AsyncSession, user):
    task_service = TaskService(session)
    tasks = await task_service.get_active_tasks()
    
    if not tasks:
        await message.answer("Нет активных заданий")
        return
    
    for task in tasks:
        # Проверяем статус задания для текущего СМИ
        assignment = await task_service.get_task_assignment(task.id, user.media_outlet)
        status = assignment.status if assignment else "new"
        
        deadline = task.deadline.strftime("%Y-%m-%d %H:%M")
        status_text = {
            'new': '🆕 Новое',
            'in_progress': '🔄 В работе',
            'completed': '✅ Выполнено'
        }.get(status, status)
        
        # Показываем кнопки в зависимости от статуса
        keyboard = None
        if status == 'new':
            keyboard = get_task_keyboard(task.id)
        elif status == 'in_progress':
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text="📝 Отправить текст",
                    callback_data=f"send_text_{task.id}"
                )
            ]])
        
        await message.answer(
            f"Задание #{task.id}\n"
            f"Пресс-релиз: {task.press_release_link}\n"
            f"Дедлайн: {deadline}\n"
            f"Статус: {status_text}",
            reply_markup=keyboard
        )

@router.message(Command("submissions"))
async def cmd_submissions(message: Message, session: AsyncSession, user):
    try:
        submission_service = SubmissionService(session)
        submissions = await submission_service.get_user_submissions(user.id)
        
        if not submissions:
            await message.answer(
                "У вас пока нет публикаций",
                reply_markup=get_media_main_keyboard()
            )
            return
        
        await message.answer(
            "Ваши публикации:",
            reply_markup=get_media_main_keyboard()
        )
        
        for submission in submissions:
            status_text = {
                'pending': '🕒 На проверке',
                'approved': '✅ Одобрено',
                'revision': '📝 Требует доработки',
                'completed': '✅ Опубликовано'
            }.get(submission.status, submission.status)
            
            text = (
                f"Публикация #{submission.id}\n"
                f"Статус: {status_text}\n"
                f"Дата отправки: {submission.submitted_at.strftime('%d.%m.%Y %H:%M')}\n"
            )
            
            if submission.revision_comment:
                text += f"Комментарий: {submission.revision_comment}\n"
            
            if submission.published_link:
                text += f"Ссылка на публикацию: {submission.published_link}\n"
            
            keyboard = None
            if submission.status == 'revision':
                keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(
                        text="Отправить исправленный текст",
                        callback_data=f"submit_revision_{submission.id}"
                    )
                ]])
            
            await message.answer(text, reply_markup=keyboard)
    
    except Exception as e:
        logging.error(f"Ошибка в обработчике cmd_submissions: {e}", exc_info=True)
        await message.answer("Произошла ошибка при получении публикаций")

@router.message(F.text == "Активные задания")
async def show_active_tasks(
    message: Message, 
    session: AsyncSession,
    user: User
):
    try:
        task_service = TaskService(session)
        tasks = await task_service.get_active_tasks()
        
        if not tasks:
            await message.answer(
                "Нет активных заданий",
                reply_markup=get_media_main_keyboard()
            )
            return
        
        for task in tasks:
            # Проверяем, взято ли задание текущим пользователем
            assignment = await task_service.get_task_assignment(task.id, user.media_outlet)
            
            # Формируем текст сообщения
            text = (
                f"Задание #{task.id}\n"
                f"Пресс-релиз: {task.press_release_link}\n"
                f"Дедлайн: {task.deadline.strftime('%d.%m.%Y %H:%M')}"
            )
            
            # Формируем клавиатуру
            if assignment:
                # Если задание уже взято, показываем кнопку "Отправить текст"
                keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(
                        text="Отправить текст",
                        callback_data=f"submit_task_{task.id}"
                    )
                ]])
            else:
                # Если задание не взято, показываем кнопку "Взять в работу"
                keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(
                        text="Взять в работу",
                        callback_data=f"take_task_{task.id}"
                    )
                ]])
            
            # Отправляем сообщение с фото или без
            if task.photo:
                await message.answer_photo(
                    photo=task.photo,
                    caption=text,
                    reply_markup=keyboard
                )
            else:
                await message.answer(
                    text,
                    reply_markup=keyboard
                )
        
    except Exception as e:
        logging.error(f"Error in show_active_tasks: {e}", exc_info=True)
        await message.answer(
            "Произошла ошибка при загрузке заданий",
            reply_markup=get_media_main_keyboard()
        )

@router.message(F.text == "Мои публикации")
async def handle_my_submissions_button(
    message: Message, 
    session: AsyncSession,
    user: User
):
    try:
        submission_service = SubmissionService(session)
        submissions = await submission_service.get_user_submissions(user.id)
        
        if not submissions:
            await message.answer(
                "У вас пока нет отправленных публикаций",
                reply_markup=get_media_main_keyboard()
            )
            return
        
        for submission in submissions:
            status_text = {
                'pending': '⏳ Ожидает проверки',
                'approved': '✅ Одобрена',
                'revision': '📝 Требует доработки',
                'rejected': '❌ Отклонена'
            }.get(submission.status, submission.status)
            
            # Добавляем кнопки в зависимости от статуса
            keyboard = None
            if submission.status == 'revision':
                keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(
                        text="Отправить исправленный текст",
                        callback_data=f"submit_revision_{submission.id}"
                    )
                ]])
            elif submission.status == 'approved' and not submission.published_link:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(
                        text="Отправить ссылку",
                        callback_data=f"send_link_{submission.id}"
                    )
                ]])
            
            if submission.photo:  # Если есть фото, отправляем его
                await message.answer_photo(
                    photo=submission.photo,
                    caption=(
                        f"Задание #{submission.task_id}, Публикация #{submission.id}\n"
                        f"Статус: {status_text}\n"
                        f"Текст: {submission.content}\n"
                        f"Отправлена: {submission.submitted_at.strftime('%d.%m.%Y %H:%M')}"
                    ),
                    reply_markup=keyboard
                )
            else:  # Если фото нет, отправляем просто текст
                await message.answer(
                    f"Задание #{submission.task_id}, Публикация #{submission.id}\n"
                    f"Статус: {status_text}\n"
                    f"Текст: {submission.content}\n"
                    f"Отправлена: {submission.submitted_at.strftime('%d.%m.%Y %H:%M')}",
                    reply_markup=keyboard
                )
        
    except Exception as e:
        logging.error(f"Error in handle_my_submissions_button: {e}", exc_info=True)
        await message.answer(
            "Произошла ошибка при получении публикаций",
            reply_markup=get_media_main_keyboard()
        )

@router.message(TaskStates.waiting_for_text)
async def handle_submission_text(
    message: Message, 
    state: FSMContext, 
    session: AsyncSession,
    user: User,
    bot: Bot
):
    try:
        data = await state.get_data()
        photo = data['photo']
        task_id = data.get('task_id')
        submission_id = data.get('submission_id')  # Добавляем получение submission_id
        
        if not task_id:
            await message.answer(
                "Ошибка: не удалось определить задание",
                reply_markup=get_media_main_keyboard()
            )
            await state.clear()
            return
        
        submission_service = SubmissionService(session)
        
        # Если это исправление существующей публикации
        if submission_id:
            # Обновляем существующую публикацию
            submission = await submission_service.update_submission_content(
                submission_id=submission_id,
                content=message.text,
                photo=photo
            )
        else:
            # Проверяем, не отправлял ли пользователь уже текст на это задание
            existing_submission = await submission_service.get_user_submission_for_task(user.id, task_id)
            if existing_submission:
                await message.answer(
                    "Вы уже отправляли текст на это задание.",
                    reply_markup=get_media_main_keyboard()
                )
                await state.clear()
                return
            
            # Создаем новую публикацию
            submission = await submission_service.create_submission(
                task_id=task_id,
                user_id=user.id,
                content=message.text,
                photo=photo
            )
        
        if not submission:
            await message.answer("Задание не найдено или было удалено")
            await state.clear()
            return
        
        # Уведомляем админов о публикации
        from src.config.users import ADMINS
        for admin in ADMINS:
            try:
                await bot.send_photo(
                    admin["telegram_id"],
                    photo=photo,
                    caption=(
                        f"📨 {'Исправленная' if submission_id else 'Новая'} публикация #{submission.id}\n"
                        f"От: {user.media_outlet}\n"
                        f"ID пользователя: {user.telegram_id}\n"
                        f"Имя пользователя: @{user.username}\n"
                        f"Задание: #{task_id}\n"
                        f"Текст публикации:\n{message.text}"
                    ),
                    reply_markup=get_moderation_keyboard(submission.id)
                )
            except Exception as e:
                print(f"Не удалось отправить уведомление администратору {admin['username']} (ID: {admin['telegram_id']}): {e}")
        
        await message.answer(
            f"✅ Публикация {'обновлена' if submission_id else 'отправлена на проверку'}",
            reply_markup=get_media_main_keyboard()
        )
        await state.clear()
        
    except Exception as e:
        logging.error(f"Error in handle_submission_text: {e}", exc_info=True)
        await message.answer(
            "Произошла ошибка при отправке публикации",
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
        'pending': '🕒 На проверке',
        'approved': '✅ Одобрено',
        'revision': '📝 Требует доработки',
        'completed': '✅ Опубликовано'
    }.get(submission.status, submission.status)
    
    text = (
        f"Публикация #{submission.id}\n"
        f"Статус: {status_text}\n"
        f"Дата отправки: {submission.submitted_at.strftime('%d.%m.%Y %H:%M')}\n"
    )
    
    if submission.revision_comment:
        text += f"Комментарий: {submission.revision_comment}\n"
    
    if submission.published_link:
        text += f"Ссылка на публикацию: {submission.published_link}\n"
    
    keyboard = None
    if submission.status == 'revision':
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(
                text="Отправить исправленный текст",
                callback_data=f"submit_revision_{submission.id}"
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
