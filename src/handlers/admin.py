from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.filters import BaseFilter
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from src.states.task_states import TaskStates, AdminStates
from src.services.task_service import TaskService
from src.services.submission_service import SubmissionService
from src.services.export_service import ExportService
from src.services.user_service import UserService
from src.keyboards.admin_kb import get_admin_main_keyboard, get_moderation_keyboard
from src.keyboards.moderation_kb import get_moderation_keyboard
from src.utils.logger import logger
from src.database.models import User, Task
from src.database.models.submission import SubmissionStatus
from src.utils.check_admin import check_admin
import logging
from typing import List
from src.handlers.media import send_user_notification

# Создаем роутер
router = Router(name='admin')

async def check_admin(user: User) -> bool:
    """Проверка на админа с логированием"""
    is_admin = int(user.is_admin) == 1
    logging.info(f"Admin check for user {user.telegram_id}:")
    logging.info(f"  is_admin value: {user.is_admin} (type: {type(user.is_admin)})")
    logging.info(f"  check result: {is_admin}")
    return is_admin

@router.callback_query(F.data == "export_reports")
async def export_reports(callback: CallbackQuery, session: AsyncSession, user: User):
    if not await check_admin(user):
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return

    try:
        logging.info(f"Admin {callback.from_user.id} called export_reports")
        logging.info(f"Callback data: {callback.data}")
        
        export_service = ExportService(session)
        filename = await export_service.export_all_tasks_report()
        
        # Отправляем файл
        await callback.message.answer_document(
            FSInputFile(filename),
            caption="Отчет по всем заданиям"
        )
        await callback.answer()
        
    except Exception as e:
        logging.error(f"Error in export_reports: {e}", exc_info=True)
        await callback.answer("Произошла ошибка при создании отчета", show_alert=True)

@router.callback_query(F.data == "create_task")
async def create_task(callback: CallbackQuery, state: FSMContext, user: User):
    if not await check_admin(user):
        logging.warning(f"Non-admin user {user.telegram_id} tried to access admin function")
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return

    logging.info(f"Admin {user.telegram_id} called create_task")
    await state.set_state(AdminStates.waiting_for_press_release)
    await callback.message.answer("Отправьте ссылку на пресс-релиз:")
    await callback.answer()

@router.message(AdminStates.waiting_for_press_release)
async def handle_press_release(message: Message, state: FSMContext):
    await state.update_data(press_release_link=message.text)
    await state.set_state(AdminStates.waiting_for_task_photo)
    await message.answer("Отправьте фото (необязательно):")

@router.message(AdminStates.waiting_for_task_photo)
async def handle_photo(message: Message, state: FSMContext):
    photo = None
    if message.photo:
        photo = message.photo[-1].file_id
        logging.info(f"Photo received: {photo}")
    
    await state.update_data(photo=photo)
    await state.set_state(AdminStates.waiting_for_deadline)
    await message.answer("Укажите дедлайн в формате ДД.ММ.ГГГГ ЧЧ:ММ")

@router.message(AdminStates.waiting_for_deadline)
async def handle_deadline(
    message: Message, 
    state: FSMContext, 
    session: AsyncSession,
    user: User,
    bot: Bot
):
    try:
        data = await state.get_data()
        press_release_link = data['press_release_link']
        photo = data.get('photo')
        logging.info(f"Creating task with photo: {photo}")
        
        # Парсим дедлайн
        deadline = datetime.strptime(message.text, "%d.%m.%Y %H:%M")
        
        # Создаем задание
        task_service = TaskService(session)
        task = await task_service.create_task(
            press_release_link=press_release_link,
            deadline=deadline,
            created_by=user.id,
            photo=photo  # Передаем фото в создание задания
        )
        
        # Уведомляем СМИ о новом задании
        user_service = UserService(session)
        media_users = await user_service.get_all_media_outlets()
        
        notification_sent = 0  # Счетчик успешно отправленных уведомлений
        for media_user in media_users:
            try:
                if task.photo:  # Если есть фото, отправляем его
                    await bot.send_photo(
                        chat_id=media_user.telegram_id,
                        photo=task.photo,
                        caption=(
                            f"[ANNOUNCE] Новое задание #{task.id}\n"
                            f"Создано администратором: @{user.username}\n"
                            f"Пресс-релиз: {task.press_release_link}\n"
                            f"Дедлайн: {task.deadline.strftime('%d.%m.%Y %H:%M')}"
                        ),
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                            InlineKeyboardButton(
                                text="Взять в работу",
                                callback_data=f"take_task_{task.id}"
                            )
                        ]])
                    )
                else:  # Если фото нет, отправляем просто текст
                    await bot.send_message(
                        chat_id=media_user.telegram_id,
                        text=(
                            f"[ANNOUNCE] Новое задание #{task.id}\n"
                            f"Создано администратором: @{user.username}\n"
                            f"Пресс-релиз: {task.press_release_link}\n"
                            f"Дедлайн: {task.deadline.strftime('%d.%m.%Y %H:%M')}"
                        ),
                        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                            InlineKeyboardButton(
                                text="Взять в работу",
                                callback_data=f"take_task_{task.id}"
                            )
                        ]])
                    )
                notification_sent += 1  # Увеличиваем счетчик, если уведомление отправлено успешно
            except Exception as e:
                print(f"Не удалось отправить уведомление пользователю {media_user.username} (ID: {media_user.telegram_id}): {e}")
        
        await message.answer(
            f"✅ Задание #{task.id} создано\n"
            f"Уведомления отправлены: {notification_sent} из {len(media_users)} СМИ",
            reply_markup=get_admin_main_keyboard()
        )
        await state.clear()
        
    except ValueError:
        await message.answer("Неверный формат даты. Пожалуйста, используйте формат ДД.ММ.ГГГГ ЧЧ:ММ")
    except Exception as e:
        logging.error(f"Error in handle_deadline: {e}", exc_info=True)
        await message.answer("Произошла ошибка при создании задания")
        await state.clear()

@router.callback_query(F.data == "review_posts")
async def review_posts(callback: CallbackQuery, session: AsyncSession, user: User):
    logging.info(f"Вызов функции review_posts пользователем {user.telegram_id}")
    try:
        if not await check_admin(user):
            logging.warning(f"Пользователь {user.telegram_id} не является администратором")
            await callback.answer("У вас нет прав администратора", show_alert=True)
            return
    
        await callback.answer("Загружаю задания...", show_alert=False)
        submission_service = SubmissionService(session)
        
        logging.info(f"Получение публикаций на модерацию для admin_id={user.id}, is_superadmin={bool(user.is_superadmin)}")
        submissions = await submission_service.get_pending_submissions(
            admin_id=user.id,
            is_superadmin=bool(user.is_superadmin)
        )
        
        logging.info(f"Получено {len(submissions)} публикаций на модерацию")
        
        if not submissions:
            logging.info("Нет публикаций на модерацию")
            await callback.message.answer("Нет публикаций на модерацию")
            return
        
        for submission in submissions:
            logging.info(f"Формирование сообщения для задания {submission.id}")
            # Формируем текст с полной информацией
            text = (
                f"[NEW] Задание #{submission.task_id}\n"
                f"От: {submission.user.media_outlet}\n"
                f"ID пользователя: {submission.user.telegram_id}\n"
                f"Имя пользователя: @{submission.user.username}\n"
                f"Создатель задания: {submission.task.created_by}\n"  # Добавляем информацию о создателе
                f"Текст задания:\n{submission.content}\n"
                f"Дата отправки: {submission.submitted_at.strftime('%d.%m.%Y %H:%M')}"
            )
            
            try:
                # Если есть фото, отправляем его с текстом
                if submission.photo:
                    logging.info(f"Отправка фото для задания {submission.id}")
                    
                    # Ограничиваем длину подписи до 850 символов
                    caption = text
                    if len(caption) > 850:
                        caption = caption[:847] + "..."
                        logging.info(f"Обрезана подпись к фото для задания {submission.id} до 850 символов")
                    
                    await callback.message.answer_photo(
                        photo=submission.photo,
                        caption=caption,
                        reply_markup=await get_moderation_keyboard(submission.id)
                    )
                else:
                    logging.info(f"Отправка текста для задания {submission.id}")
                    
                    # Ограничиваем длину текста до 4000 символов (максимальный размер сообщения в Telegram)
                    message_text = text
                    if len(message_text) > 4000:
                        message_text = message_text[:3997] + "..."
                        logging.info(f"Обрезан текст для задания {submission.id} до 4000 символов")
                    
                    await callback.message.answer(
                        message_text,
                        reply_markup=await get_moderation_keyboard(submission.id)
                    )
            except Exception as e:
                logging.error(f"Ошибка при отправке сообщения для задания {submission.id}: {e}", exc_info=True)
                # Пробуем отправить короткую версию при ошибке
                try:
                    short_text = (
                        f"[NEW] Задание #{submission.task_id}\n"
                        f"От: {submission.user.media_outlet}\n"
                        f"Имя пользователя: @{submission.user.username}\n"
                        f"(Текст задания слишком длинный и был обрезан)"
                    )
                    
                    if submission.photo:
                        await callback.message.answer_photo(
                            photo=submission.photo,
                            caption=short_text[:850],
                            reply_markup=await get_moderation_keyboard(submission.id)
                        )
                    else:
                        await callback.message.answer(
                            short_text,
                            reply_markup=await get_moderation_keyboard(submission.id)
                        )
                except Exception as nested_e:
                    logging.error(f"Вторичная ошибка при отправке сообщения: {nested_e}", exc_info=True)
        
    except Exception as e:
        logging.error(f"Ошибка в функции review_posts: {e}", exc_info=True)
        await callback.message.answer("Произошла ошибка при получении заданий на модерацию")
        await callback.answer("Произошла ошибка", show_alert=True)

@router.callback_query(F.data.startswith("approve_submission_"))
async def approve_submission(callback: CallbackQuery, session: AsyncSession, user: User, bot: Bot):
    if not await check_admin(user):
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return

    submission_id = int(callback.data.split("_")[-1])
    submission_service = SubmissionService(session)

    try:
        # Получаем задание с данными пользователя
        submission = await submission_service.get_submission_with_user(submission_id)
        if not submission:
            await callback.answer("Задание не найдено", show_alert=True)
            return

        # Проверяем права на модерацию (суперадмин или создатель задания)
        is_superadmin = bool(user.is_superadmin)
        is_task_creator = submission.task.created_by == user.id
        
        if not (is_superadmin or is_task_creator):
            logging.warning(f"Пользователь {user.id} попытался модерировать не своё задание {submission.task_id}")
            await callback.answer("У вас нет прав на модерацию этого задания", show_alert=True)
            return

        # Пытаемся одобрить задание
        try:
            submission = await submission_service.approve_submission(submission_id)
            logging.info(f"Submission {submission_id} approved successfully")
        except ValueError as e:
            await callback.answer(str(e), show_alert=True)
            return

        # Формируем текст сообщения
        if callback.message.text:
            message_text = callback.message.text + "\n\nСтатус: Одобрено ✅"
            await callback.message.edit_text(
                message_text,
                reply_markup=callback.message.reply_markup
            )
        elif callback.message.caption:
            message_text = callback.message.caption + "\n\nСтатус: Одобрено ✅"
            await callback.message.edit_caption(
                message_text,
                reply_markup=callback.message.reply_markup
            )
        else:
            message_text = f"[NEW] Задание #{submission.task_id} одобрено ✅"
            await callback.message.edit_text(
                message_text,
                reply_markup=callback.message.reply_markup
            )
            
        # Отправляем уведомление пользователю о статусе публикации
        await send_user_notification(bot, submission)
        
        # Сообщаем об успешной операции
        await callback.answer("Публикация одобрена")
        
    except Exception as e:
        logging.error(f"Error in approve_submission: {e}", exc_info=True)
        await callback.answer("Произошла ошибка при одобрении публикации", show_alert=True)

@router.callback_query(F.data.startswith("request_revision_"))
async def request_revision(callback: CallbackQuery, state: FSMContext, session: AsyncSession, user: User):
    if not await check_admin(user):
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return

    try:
        submission_id = int(callback.data.split("_")[-1])
        
        # Получаем задание для проверки статуса
        submission_service = SubmissionService(session)
        submission = await submission_service.get_submission_with_user(submission_id)
        
        if not submission:
            await callback.answer("Задание не найдено", show_alert=True)
            return
        
        # Проверяем права на модерацию (суперадмин или создатель задания)
        is_superadmin = bool(user.is_superadmin)
        is_task_creator = submission.task.created_by == user.id
        
        if not (is_superadmin or is_task_creator):
            logging.warning(f"Пользователь {user.id} попытался отправить на доработку не своё задание {submission.task_id}")
            await callback.answer("У вас нет прав на модерацию этого задания", show_alert=True)
            return
            
        # Проверяем возможность отправки на доработку
        if submission.status == SubmissionStatus.REVISION.value:
            await callback.message.answer("❌ Задание уже находится на доработке")
            await callback.answer()
            return
        elif submission.status == SubmissionStatus.COMPLETED.value:
            await callback.message.answer("❌ Нельзя отправить на доработку завершенное задание")
            await callback.answer()
            return
        elif submission.status == SubmissionStatus.APPROVED.value:
            await callback.message.answer("❌ Нельзя отправить на доработку одобренное задание")
            await callback.answer()
            return
            
        # Определяем тип контента для доработки
        is_photo_revision = False
        if submission.status == SubmissionStatus.PHOTO_PENDING.value:
            is_photo_revision = True
        elif submission.photo and submission.status == SubmissionStatus.REVISION.value:
            is_photo_revision = True
            
        await state.update_data(
            submission_id=submission_id,
            is_photo_revision=is_photo_revision,
            can_send_text=True
        )
        await state.set_state(TaskStates.waiting_for_revision)
        
        content_type = "фото" if is_photo_revision else "текста"
        await callback.message.answer(f"Введите комментарий для доработки {content_type}:")
        await callback.answer()
        
    except Exception as e:
        logging.error(f"Error in request_revision: {e}", exc_info=True)
        await callback.message.answer("[ERROR] Произошла ошибка при запросе доработки")
        await callback.answer()

@router.message(TaskStates.waiting_for_revision)
async def handle_revision_comment(
    message: Message, 
    state: FSMContext, 
    session: AsyncSession,
    bot: Bot
):
    try:
        data = await state.get_data()
        submission_id = data.get('submission_id')
        is_photo_revision = data.get('is_photo_revision', False)
        
        if not submission_id:
            await state.clear()
            await message.answer("Произошла ошибка: не найден ID задания")
            return

        submission_service = SubmissionService(session)
        
        try:
            # Запрашиваем доработку
            submission = await submission_service.request_revision(
                submission_id=submission_id,
                comment=message.text,
                is_photo_revision=is_photo_revision
            )
            
            # Получаем обновленное задание с данными пользователя
            submission = await submission_service.get_submission_with_user(submission_id)
            
            if not submission.user:
                await state.clear()
                await message.answer("Произошла ошибка: пользователь не найден")
                return
                
            if not submission.user.telegram_id:
                await state.clear()
                await message.answer("Произошла ошибка: не найден Telegram ID пользователя")
                return
            
            # Отправляем уведомление пользователю
            content_type = "фото" if is_photo_revision else "текста"
            try:
                await bot.send_message(
                    chat_id=submission.user.telegram_id,
                    text=f"⚠️ {content_type.capitalize()} для задания #{submission.task_id} требует доработки.\n"
                         f"Комментарий от администратора @{message.from_user.username}:\n{message.text}",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                        InlineKeyboardButton(
                            text="Отправить исправленный текст",
                            callback_data=f"submit_revision_{submission.id}"
                        )
                    ]])
                )
            except Exception as e:
                logging.error(f"Error sending revision notification to user: {e}")
                await message.answer("Ошибка при отправке уведомления пользователю")
            
            await message.answer("✅ Комментарий отправлен пользователю")
            await state.clear()
            
        except ValueError as e:
            await state.clear()
            await message.answer(
                f"Ошибка: {str(e)}\n\n"
                "Попробуйте снова через админ панель",
                reply_markup=get_admin_main_keyboard()
            )
            return
        
    except Exception as e:
        logging.error(f"Error in handle_revision_comment: {e}", exc_info=True)
        await state.clear()
        await message.answer(
            "Произошла ошибка при обработке комментария.\n"
            "Попробуйте снова через админ панель",
            reply_markup=get_admin_main_keyboard()
        )

@router.message(Command("create"))
async def cmd_create(message: Message, state: FSMContext, user: User):
    if not await check_admin(user):
        await message.answer("У вас нет прав администратора")
        return

    await state.set_state(AdminStates.waiting_for_press_release)
    await message.answer("Отправьте ссылку на пресс-релиз:")

@router.message(Command("review"))
async def cmd_review(message: Message, session: AsyncSession, user: User):
    logging.info(f"Вызов команды /review пользователем {user.telegram_id}")
    try:
        if not await check_admin(user):
            logging.warning(f"Пользователь {user.telegram_id} не является администратором")
            await message.answer("У вас нет прав администратора")
            return
    
        await message.answer("Загружаю задания на модерацию...")
        
        submission_service = SubmissionService(session)
        submissions = await submission_service.get_pending_submissions(
            admin_id=user.id,
            is_superadmin=bool(user.is_superadmin)
        )
        
        logging.info(f"Получено {len(submissions)} заданий на модерацию")
        
        if not submissions:
            logging.info("Нет заданий на модерацию")
            await message.answer("Нет заданий на модерацию")
            return
        
        for submission in submissions:
            logging.info(f"Формирование сообщения для задания {submission.id}")
            # Формируем текст с полной информацией
            text = (
                f"📨 Задание #{submission.task_id}\n"
                f"От: {submission.user.media_outlet}\n"
                f"ID пользователя: {submission.user.telegram_id}\n"
                f"Имя пользователя: @{submission.user.username}\n"
                f"Создатель задания: {submission.task.created_by}\n"  # Добавляем информацию о создателе
                f"Текст задания:\n{submission.content}\n"
                f"Дата отправки: {submission.submitted_at.strftime('%d.%m.%Y %H:%M')}"
            )
            
            try:
                # Если есть фото, отправляем его с текстом
                if submission.photo:
                    logging.info(f"Отправка фото для задания {submission.id}")
                    
                    # Ограничиваем длину подписи до 850 символов
                    caption = text
                    if len(caption) > 850:
                        caption = caption[:847] + "..."
                        logging.info(f"Обрезана подпись к фото для задания {submission.id} до 850 символов")
                    
                    await message.answer_photo(
                        photo=submission.photo,
                        caption=caption,
                        reply_markup=await get_moderation_keyboard(submission.id)
                    )
                else:
                    logging.info(f"Отправка текста для задания {submission.id}")
                    
                    # Ограничиваем длину текста до 4000 символов (максимальный размер сообщения в Telegram)
                    message_text = text
                    if len(message_text) > 4000:
                        message_text = message_text[:3997] + "..."
                        logging.info(f"Обрезан текст для задания {submission.id} до 4000 символов")
                    
                    await message.answer(
                        message_text,
                        reply_markup=await get_moderation_keyboard(submission.id)
                    )
            except Exception as e:
                logging.error(f"Ошибка при отправке сообщения для задания {submission.id}: {e}", exc_info=True)
                # Пробуем отправить короткую версию при ошибке
                try:
                    short_text = (
                        f"📨 Задание #{submission.task_id}\n"
                        f"От: {submission.user.media_outlet}\n"
                        f"Имя пользователя: @{submission.user.username}\n"
                        f"(Текст задания слишком длинный и был обрезан)"
                    )
                    
                    if submission.photo:
                        await message.answer_photo(
                            photo=submission.photo,
                            caption=short_text[:850],
                            reply_markup=await get_moderation_keyboard(submission.id)
                        )
                    else:
                        await message.answer(
                            short_text,
                            reply_markup=await get_moderation_keyboard(submission.id)
                        )
                except Exception as nested_e:
                    logging.error(f"Вторичная ошибка при отправке сообщения: {nested_e}", exc_info=True)
                    
    except Exception as e:
        logging.error(f"Ошибка в функции cmd_review: {e}", exc_info=True)
        await message.answer("Произошла ошибка при получении заданий на модерацию")

@router.message(Command("export"))
async def cmd_export(message: Message, session: AsyncSession, user: User):
    if not await check_admin(user):
        await message.answer("У вас нет прав администратора")
        return

    try:
        export_service = ExportService(session)
        filename = await export_service.export_all_tasks_report()
        
        await message.answer_document(
            FSInputFile(filename),
            caption="Отчет по всем заданиям"
        )
        
    except Exception as e:
        logging.error(f"Error in export_reports: {e}", exc_info=True)
        await message.answer("Произошла ошибка при создании отчета")

@router.message(Command("admin"))
async def handle_admin_command(message: Message, user: User, state: FSMContext):
    try:
        # Сначала очищаем состояние
        await state.clear()
        
        if not await check_admin(user):
            await message.answer("❌ У вас нет прав администратора")
            return
        
        await message.answer(
            "Добро пожаловать в панель администратора!",
            reply_markup=get_admin_main_keyboard()
        )
        
    except Exception as e:
        logging.error(f"Error in handle_admin_command: {e}", exc_info=True)
        await message.answer(f"Произошла ошибка при открытии админ панели: {str(e)}")
        await state.clear()

@router.callback_query(F.data.startswith("review_submission_"))
async def review_submission(callback: CallbackQuery, session: AsyncSession):
    submission_id = int(callback.data.split("_")[-1])
    logging.info(f"Запрос просмотра задания {submission_id}")
    submission_service = SubmissionService(session)
    submission = await submission_service.get_submission_with_user(submission_id)

    if submission.content is None:
        await callback.answer("Текст задания отсутствует.")
        return

    text = (
        f"[NEW] Задание #{submission.task_id}\n"
        f"От: {submission.user.media_outlet}\n"
        f"Задание: #{submission.task_id}\n"
        f"Текст задания:\n{submission.content}"
    )

    try:
        # Ограничиваем длину текста до 4000 символов
        message_text = text
        if len(message_text) > 4000:
            message_text = message_text[:3997] + "..."
            logging.info(f"Обрезан текст для задания {submission.id} до 4000 символов")
        
        await callback.message.answer(
            message_text,
            reply_markup=await get_moderation_keyboard(submission.id)
        )
        await callback.answer()
    except Exception as e:
        logging.error(f"Ошибка при отправке деталей задания {submission_id}: {e}", exc_info=True)
        
        # Пробуем отправить короткую версию при ошибке
        try:
            short_text = (
                f"[NEW] Задание #{submission.task_id}\n"
                f"От: {submission.user.media_outlet}\n"
                f"(Текст задания слишком длинный и был обрезан)"
            )
            
            await callback.message.answer(
                short_text,
                reply_markup=await get_moderation_keyboard(submission.id)
            )
        except Exception as nested_e:
            logging.error(f"Вторичная ошибка при отправке сообщения: {nested_e}", exc_info=True)
            
        await callback.answer("Произошла ошибка при отображении деталей задания", show_alert=True)

@router.callback_query(F.data.startswith("send_link_"))
async def handle_send_link(callback: CallbackQuery, state: FSMContext):
    submission_id = int(callback.data.split("_")[-1])
    
    # Сохраняем ID задания в состоянии
    await state.update_data(submission_id=submission_id)
    
    # Переводим пользователя в состояние ожидания ссылки
    await state.set_state(TaskStates.waiting_for_link)
    
    await callback.message.answer("Пожалуйста, отправьте ссылку на пресс-релиз:")
    await callback.answer()

@router.message(TaskStates.waiting_for_link)
async def handle_link_submission(
    message: Message, 
    state: FSMContext, 
    session: AsyncSession,
    bot: Bot
):
    data = await state.get_data()
    submission_id = data['submission_id']
    
    submission_service = SubmissionService(session)
    
    try:
        # Проверяем существование задания
        submission = await submission_service.get_submission(submission_id)
        if not submission:
            await message.answer("Задание не найдено. Возможно, оно было удалено.")
            await state.clear()
            return
        
        # Добавляем ссылку на задание
        submission = await submission_service.add_published_link(submission_id, message.text)
        
        # Готовим текст уведомления
        notification_text = (
            f"ℹ️ Информация о задании\n"
            f"Пользователь @{message.from_user.username} отправил ссылку на задание #{submission.task_id}:\n"
            f"{message.text}"
        )
        
        # Получаем ТОЛЬКО суперадминов из базы данных
        user_service = UserService(session)
        superadmins = await user_service.get_superadmins()
        logging.info(f"Найдено {len(superadmins)} суперадминов в базе данных")
        
        # Множество для отслеживания уже уведомленных пользователей
        notified_user_telegrams = set()
        
        # Отправляем уведомления всем суперадминам
        notified_count = 0
        for admin in superadmins:
            try:
                if admin.telegram_id:
                    try:
                        # Преобразуем telegram_id к int
                        admin_telegram_id = int(admin.telegram_id)
                        
                        # Отправляем уведомление
                        await bot.send_message(
                            admin_telegram_id,
                            notification_text
                        )
                        notified_user_telegrams.add(admin_telegram_id)
                        notified_count += 1
                        logging.info(f"✅ Уведомление отправлено суперадмину {admin.username} (ID: {admin_telegram_id})")
                    except (ValueError, TypeError) as e:
                        logging.error(f"❌ Ошибка преобразования telegram_id для {admin.username}: {e}")
                else:
                    logging.warning(f"⚠️ У суперадмина {admin.username} отсутствует telegram_id")
            except Exception as e:
                logging.error(f"Не удалось отправить уведомление суперадмину {admin.username}: {e}")
        
        # Получаем задание, чтобы узнать его создателя
        task_service = TaskService(session)
        task = await task_service.get_task_by_id(submission.task_id)
        
        # Получаем создателя задания и отправляем ему уведомление, если он еще не получил его как суперадмин
        if task and task.created_by:
            creator = await user_service.get_user_by_id(task.created_by)
            if creator and creator.telegram_id:
                try:
                    creator_telegram_id = int(creator.telegram_id)
                    
                    # Проверяем, не получил ли создатель уже уведомление как суперадмин
                    if creator_telegram_id not in notified_user_telegrams:
                        await bot.send_message(
                            creator_telegram_id,
                            notification_text
                        )
                        notified_count += 1
                        logging.info(f"✅ Уведомление отправлено создателю задания {creator.username} (ID: {creator_telegram_id})")
                except Exception as e:
                    logging.error(f"Не удалось отправить уведомление создателю задания {creator.username if creator else 'unknown'}: {e}")
        
        logging.info(f"📊 Отправлено уведомлений {notified_count} пользователям (суперадмины + создатель задания)")
        
        await message.answer("✅ Ссылка успешно отправлена!")
        await state.clear()
        
    except Exception as e:
        logging.error(f"Ошибка при обработке ссылки: {e}")
        await message.answer("Произошла ошибка при обработке ссылки. Пожалуйста, попробуйте еще раз.")
        await state.clear()

@router.callback_query(F.data.startswith("delete_task_"))
async def delete_task(
    callback: CallbackQuery, 
    session: AsyncSession,
    user: User
):
    if not await check_admin(user):
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return

    task_id = int(callback.data.split("_")[-1])
    task_service = TaskService(session)
    
    try:
        # Удаляем задание и все связанные данные
        await task_service.delete_task_with_related_data(task_id)
        
        await callback.answer("[ERROR] Задание и все связанные данные успешно удалены [OK]")
        
        # Удаляем сообщение с заданием
        await callback.message.delete()
        
    except Exception as e:
        logging.error(f"Error deleting task {task_id}: {e}")
        await callback.answer("Произошла ошибка при удалении задания", show_alert=True)

@router.callback_query(F.data == "list_tasks_for_deletion")
async def list_tasks_for_deletion(
    callback: CallbackQuery, 
    session: AsyncSession,
    user: User
):
    if not await check_admin(user):
        await callback.answer("У вас нет прав администратора", show_alert=True)
        return

    task_service = TaskService(session)
    tasks = await task_service.get_all_tasks()
    
    if not tasks:
        await callback.message.answer("Нет заданий для удаления")
        return
    
    # Отправляем каждое задание отдельным сообщением
    for task in tasks:
        # Обрезаем ссылку если она слишком длинная
        press_release_link = task.press_release_link
        if len(press_release_link) > 300:
            press_release_link = press_release_link[:297] + "..."
            
        task_text = (
            f"Задание #{task.id}\n"
            f"Дедлайн: {task.deadline.strftime('%d.%m.%Y %H:%M')}\n"
            f"Статус: {task.status}\n"
            f"Пресс-релиз: {press_release_link}"
        )
        
        # Если есть фото, отправляем с фото
        if task.photo:
            try:
                await callback.message.answer_photo(
                    photo=task.photo,
                    caption=task_text,
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                        InlineKeyboardButton(
                            text="❌ Удалить",
                            callback_data=f"delete_task_{task.id}"
                        )
                    ]])
                )
            except Exception as e:
                logging.error(f"Error sending task {task.id} with photo: {e}")
                # Если не удалось отправить с фото, отправляем без него
                await callback.message.answer(
                    task_text,
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                        InlineKeyboardButton(
                            text="❌ Удалить",
                            callback_data=f"delete_task_{task.id}"
                        )
                    ]])
                )
        else:
            await callback.message.answer(
                task_text,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                    InlineKeyboardButton(
                        text="❌ Удалить",
                        callback_data=f"delete_task_{task.id}"
                    )
                ]])
            )
    
    await callback.answer()

def get_admin_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Создать задание", callback_data="create_task"),
            InlineKeyboardButton(text="Просмотр публикаций", callback_data="review_posts")
        ],
        [
            InlineKeyboardButton(text="Экспорт отчётов", callback_data="export_reports"),
            InlineKeyboardButton(text="Список заданий", callback_data="list_tasks_for_deletion")  # Измененная кнопка
        ]
    ])

async def notify_media_about_new_task(
    bot: Bot, 
    task: Task, 
    media_users: List[User]
):
    for user in media_users:
        try:
            if task.photo:
                await bot.send_photo(
                    chat_id=user.telegram_id,
                    photo=task.photo,
                    caption=(
                        f"[ANNOUNCE] Новое задание #{task.id}\n"
                        f"Пресс-релиз: {task.press_release_link}\n"
                        f"Дедлайн: {task.deadline.strftime('%d.%m.%Y %H:%M')}"
                    ),
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                        InlineKeyboardButton(
                            text="Взять в работу",
                            callback_data=f"take_task_{task.id}"
                        )
                    ]])
                )
            else:
                await bot.send_message(
                    chat_id=user.telegram_id,
                    text=(
                        f"[ANNOUNCE] Новое задание #{task.id}\n"
                        f"Пресс-релиз: {task.press_release_link}\n"
                        f"Дедлайн: {task.deadline.strftime('%d.%m.%Y %H:%M')}"
                    ),
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                        InlineKeyboardButton(
                            text="Взять в работу",
                            callback_data=f"take_task_{task.id}"
                        )
                    ]])
                )
        except Exception as e:
            logging.error(f"Не удалось отправить уведомление пользователю {user.username} (ID: {user.telegram_id}): {e}")

@router.message(AdminStates.waiting_for_task_photo)
async def handle_task_photo(
    message: Message, 
    state: FSMContext, 
    session: AsyncSession,
    user: User
):
    try:
        if not message.photo:
            await message.answer("Пожалуйста, прикрепите фото к заданию.")
            return
        
        # Получаем данные из состояния
        data = await state.get_data()
        press_release_link = data['press_release_link']
        deadline = data['deadline']
        
        # Сохраняем фото
        photo = message.photo[-1].file_id
        
        # Создаем задание
        task_service = TaskService(session)
        task = await task_service.create_task(
            press_release_link=press_release_link,
            deadline=deadline,
            created_by=user.id,
            photo=photo
        )
        
        # Уведомляем СМИ
        media_users = await task_service.get_media_users()
        await notify_media_about_new_task(message.bot, task, media_users)
        
        await message.answer(
            f"✅ Задание #{task.id} успешно создано",
            reply_markup=get_admin_main_keyboard()
        )
        await state.clear()
        
    except Exception as e:
        logging.error(f"Error in handle_task_photo: {e}", exc_info=True)
        await message.answer(
            "Произошла ошибка при создании задания",
            reply_markup=get_admin_main_keyboard()
        )
        await state.clear()

@router.callback_query(F.data.startswith("request_link_"))
async def request_link(callback: CallbackQuery, session: AsyncSession, bot: Bot, user: User):
    try:
        if not await check_admin(user):
            await callback.answer("У вас нет прав администратора", show_alert=True)
            return
            
        submission_id = int(callback.data.split("_")[-1])
        
        # Получаем задание с данными пользователя
        submission_service = SubmissionService(session)
        submission = await submission_service.get_submission_with_user(submission_id)
        
        if not submission:
            await callback.answer("Задание не найдено", show_alert=True)
            return
            
        if not submission.user:
            await callback.answer("Пользователь не найден", show_alert=True)
            return
        
        # Проверяем права на модерацию (суперадмин или создатель задания)
        is_superadmin = bool(user.is_superadmin)
        is_task_creator = submission.task.created_by == user.id
        
        if not (is_superadmin or is_task_creator):
            logging.warning(f"Пользователь {user.id} попытался запросить ссылку для не своего задания {submission.task_id}")
            await callback.answer("У вас нет прав на модерацию этого задания", show_alert=True)
            return
            
        # Отправляем уведомление пользователю
        await bot.send_message(
            chat_id=submission.user.telegram_id,
            text=f"🔗 Пожалуйста, отправьте ссылку на опубликованный материал для задания #{submission.task_id}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(
                    text="Отправить ссылку",
                    callback_data=f"send_link_{submission.id}"
                )
            ]])
        )
        
        # Отправляем подтверждение админу
        await callback.answer("Запрос на предоставление ссылки отправлен")
        
    except Exception as e:
        logging.error(f"Error in request_link: {e}", exc_info=True)
        await callback.answer("Произошла ошибка при запросе ссылки", show_alert=True)