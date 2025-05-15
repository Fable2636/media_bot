from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from src.states.superadmin_states import SuperadminStates
from src.services.superadmin_service import SuperadminService
from src.database.models import User
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import logging

router = Router(name='superadmin')

async def check_superadmin(user: User) -> bool:
    """Проверяет, является ли пользователь суперадмином"""
    logging.info(f"Checking superadmin status for user {user.telegram_id}")
    logging.info(f"User data: {user.__dict__}")
    is_superadmin = bool(user.is_superadmin)
    logging.info(f"Is superadmin: {is_superadmin}")
    return is_superadmin

def get_superadmin_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру для суперадмина"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Добавить админа", callback_data="add_admin"),
            InlineKeyboardButton(text="Удалить админа", callback_data="remove_admin")
        ],
        [
            InlineKeyboardButton(text="Добавить СМИ", callback_data="add_media"),
            InlineKeyboardButton(text="Удалить СМИ", callback_data="remove_media")
        ],
        [
            InlineKeyboardButton(text="Список админов", callback_data="list_admins"),
            InlineKeyboardButton(text="Список СМИ", callback_data="list_media")
        ],
        [
            InlineKeyboardButton(text="Управление суперадминами", callback_data="manage_superadmins")
        ]
    ])

@router.message(Command("superadmin"))
async def cmd_superadmin(message: Message, user: User):
    """Обработчик команды /superadmin"""
    if not await check_superadmin(user):
        await message.answer("У вас нет прав суперадмина")
        return
        
    await message.answer(
        "Панель управления суперадмина",
        reply_markup=get_superadmin_keyboard()
    )

@router.callback_query(F.data == "add_admin")
async def add_admin_start(callback: CallbackQuery, state: FSMContext, user: User):
    if not await check_superadmin(user):
        await callback.answer("У вас нет прав суперадмина", show_alert=True)
        return
        
    await state.set_state(SuperadminStates.waiting_for_admin_id)
    await callback.message.answer("Введите Telegram ID нового администратора:")
    await callback.answer()

@router.message(SuperadminStates.waiting_for_admin_id)
async def add_admin_id(message: Message, state: FSMContext):
    try:
        admin_id = int(message.text)
        await state.update_data(admin_id=admin_id)
        await state.set_state(SuperadminStates.waiting_for_admin_username)
        await message.answer("Введите username администратора:")
    except ValueError:
        await message.answer("Пожалуйста, введите корректный Telegram ID (только цифры)")

@router.message(SuperadminStates.waiting_for_admin_username)
async def add_admin_username(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    admin_id = data['admin_id']
    username = message.text.strip()
    
    service = SuperadminService(session)
    try:
        admin = await service.add_admin(admin_id, username)
        # Проверим, что is_admin установлен корректно
        logging.info(f"Проверка созданного админа: id={admin.id}, telegram_id={admin.telegram_id}, "
                   f"username={admin.username}, is_admin={admin.is_admin} (тип: {type(admin.is_admin)})")
                   
        # Если is_admin не имеет значение True, корректируем это
        if admin.is_admin is not True:
            logging.warning(f"Обнаружено некорректное значение is_admin={admin.is_admin}, "
                          f"устанавливаем явный True")
            admin.is_admin = True
            await session.commit()
            
        await message.answer(f"✅ Администратор успешно добавлен:\nID: {admin.telegram_id}\nUsername: {admin.username}")
    except Exception as e:
        await message.answer(f"❌ Ошибка при добавлении администратора: {str(e)}")
    finally:
        await state.clear()

@router.callback_query(F.data == "remove_admin")
async def remove_admin_start(callback: CallbackQuery, state: FSMContext, user: User, session: AsyncSession):
    if not await check_superadmin(user):
        await callback.answer("У вас нет прав суперадмина", show_alert=True)
        return
        
    service = SuperadminService(session)
    admins = await service.get_all_admins()
    
    if not admins:
        await callback.message.answer("Нет администраторов для удаления")
        return
        
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"@{admin.username} ({admin.telegram_id})",
            callback_data=f"remove_admin_{admin.telegram_id}"
        )] for admin in admins if not admin.is_superadmin
    ])
    
    await callback.message.answer("Выберите администратора для удаления:", reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data.startswith("remove_admin_"))
async def remove_admin_confirm(callback: CallbackQuery, session: AsyncSession, user: User):
    if not await check_superadmin(user):
        await callback.answer("У вас нет прав суперадмина", show_alert=True)
        return
        
    admin_id = int(callback.data.split("_")[-1])
    service = SuperadminService(session)
    
    try:
        await service.remove_admin(admin_id)
        await callback.message.answer(f"✅ Администратор с ID {admin_id} успешно удален")
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка при удалении администратора: {str(e)}")
    
    await callback.answer()

@router.callback_query(F.data == "add_media")
async def add_media_start(callback: CallbackQuery, state: FSMContext, user: User):
    if not await check_superadmin(user):
        await callback.answer("У вас нет прав суперадмина", show_alert=True)
        return
        
    await state.set_state(SuperadminStates.waiting_for_media_id)
    await callback.message.answer("Введите Telegram ID нового представителя СМИ:")
    await callback.answer()

@router.message(SuperadminStates.waiting_for_media_id)
async def add_media_id(message: Message, state: FSMContext):
    try:
        media_id = int(message.text)
        await state.update_data(media_id=media_id)
        await state.set_state(SuperadminStates.waiting_for_media_username)
        await message.answer("Введите username представителя СМИ:")
    except ValueError:
        await message.answer("Пожалуйста, введите корректный Telegram ID (только цифры)")

@router.message(SuperadminStates.waiting_for_media_username)
async def add_media_username(message: Message, state: FSMContext):
    username = message.text.strip()
    await state.update_data(username=username)
    await state.set_state(SuperadminStates.waiting_for_media_outlet)
    await message.answer("Введите название СМИ:")

@router.message(SuperadminStates.waiting_for_media_outlet)
async def add_media_outlet(message: Message, state: FSMContext, session: AsyncSession):
    data = await state.get_data()
    media_id = data['media_id']
    username = data['username']
    media_outlet = message.text.strip()
    
    service = SuperadminService(session)
    try:
        media = await service.add_media_outlet(media_id, username, media_outlet)
        await message.answer(
            f"✅ Представитель СМИ успешно добавлен:\n"
            f"ID: {media.telegram_id}\n"
            f"Username: {media.username}\n"
            f"СМИ: {media.media_outlet}"
        )
    except Exception as e:
        await message.answer(f"❌ Ошибка при добавлении представителя СМИ: {str(e)}")
    finally:
        await state.clear()

@router.callback_query(F.data == "remove_media")
async def remove_media_start(callback: CallbackQuery, session: AsyncSession, user: User):
    if not await check_superadmin(user):
        await callback.answer("У вас нет прав суперадмина", show_alert=True)
        return
        
    service = SuperadminService(session)
    media_outlets = await service.get_all_media_outlets()
    
    if not media_outlets:
        await callback.message.answer("Нет представителей СМИ для удаления")
        return
        
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"@{media.username} - {media.media_outlet}",
            callback_data=f"remove_media_{media.telegram_id}"
        )] for media in media_outlets
    ])
    
    await callback.message.answer("Выберите представителя СМИ для удаления:", reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data.startswith("remove_media_"))
async def remove_media_confirm(callback: CallbackQuery, session: AsyncSession, user: User):
    if not await check_superadmin(user):
        await callback.answer("У вас нет прав суперадмина", show_alert=True)
        return
        
    media_id = int(callback.data.split("_")[-1])
    service = SuperadminService(session)
    
    try:
        await service.remove_media_outlet(media_id)
        await callback.message.answer(f"✅ Представитель СМИ с ID {media_id} успешно удален")
    except Exception as e:
        await callback.message.answer(f"❌ Ошибка при удалении представителя СМИ: {str(e)}")
    
    await callback.answer()

@router.callback_query(F.data == "list_admins")
async def list_admins(callback: CallbackQuery, session: AsyncSession, user: User):
    if not await check_superadmin(user):
        await callback.answer("У вас нет прав суперадмина", show_alert=True)
        return
        
    service = SuperadminService(session)
    admins = await service.get_all_admins()
    
    if not admins:
        await callback.message.answer("Список администраторов пуст")
        return
        
    message_text = "📋 Список администраторов:\n\n"
    for admin in admins:
        role = "Суперадмин" if admin.is_superadmin else "Админ"
        message_text += f"• @{admin.username} ({admin.telegram_id}) - {role}\n"
    
    await callback.message.answer(message_text)
    await callback.answer()

@router.callback_query(F.data == "list_media")
async def list_media(callback: CallbackQuery, session: AsyncSession, user: User):
    if not await check_superadmin(user):
        await callback.answer("У вас нет прав суперадмина", show_alert=True)
        return
        
    service = SuperadminService(session)
    media_outlets = await service.get_all_media_outlets()
    
    if not media_outlets:
        await callback.message.answer("Список представителей СМИ пуст")
        return
        
    message_text = "📋 Список представителей СМИ:\n\n"
    for media in media_outlets:
        message_text += f"• @{media.username} ({media.telegram_id}) - {media.media_outlet}\n"
    
    await callback.message.answer(message_text)
    await callback.answer()

@router.callback_query(F.data == "manage_superadmins")
async def manage_superadmins(callback: CallbackQuery, session: AsyncSession, user: User):
    if not await check_superadmin(user):
        await callback.answer("У вас нет прав суперадмина", show_alert=True)
        return
        
    service = SuperadminService(session)
    admins = await service.get_all_admins()
    
    if not admins:
        await callback.message.answer("Нет администраторов")
        return
        
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"{'🔴' if not admin.is_superadmin else '🟢'} @{admin.username}",
            callback_data=f"toggle_superadmin_{admin.telegram_id}"
        )] for admin in admins
    ])
    
    await callback.message.answer(
        "Управление суперадминами:\n"
        "🔴 - обычный админ\n"
        "🟢 - суперадмин\n"
        "Нажмите на админа для изменения статуса:",
        reply_markup=keyboard
    )
    await callback.answer()

@router.callback_query(F.data.startswith("toggle_superadmin_"))
async def toggle_superadmin_status(callback: CallbackQuery, session: AsyncSession, user: User):
    if not await check_superadmin(user):
        await callback.answer("У вас нет прав суперадмина", show_alert=True)
        return
        
    target_id = int(callback.data.split("_")[-1])
    service = SuperadminService(session)
    
    try:
        updated_user = await service.toggle_superadmin(target_id)
        new_status = "суперадмин" if updated_user.is_superadmin else "обычный админ"
        await callback.message.answer(
            f"Статус пользователя @{updated_user.username} изменен на: {new_status}"
        )
        # Обновляем список
        await manage_superadmins(callback, session, user)
    except Exception as e:
        await callback.message.answer(f"Ошибка при изменении статуса: {str(e)}")
    
    await callback.answer() 