from src.config.users import ADMINS
from src.database.models import User
import logging

async def check_admin(user: User) -> bool:
    """
    Проверяет, является ли пользователь администратором или суперадмином
    
    Args:
        user (User): Объект пользователя
        
    Returns:
        bool: True если пользователь администратор или суперадмин, False в противном случае
    """
    try:
        # Проверяем, есть ли пользователь в списке администраторов
        is_in_admins = any(admin["telegram_id"] == user.telegram_id for admin in ADMINS)
        
        # Проверяем флаги в базе данных
        is_admin_in_db = bool(user.is_admin)
        is_superadmin = bool(user.is_superadmin)
        
        # Пользователь должен быть либо суперадмином, либо обычным админом
        is_admin = is_superadmin or (is_in_admins and is_admin_in_db)
        
        logging.info(f"Admin check for user {user.telegram_id}:")
        logging.info(f"  In ADMINS list: {is_in_admins}")
        logging.info(f"  DB is_admin value: {user.is_admin} (type: {type(user.is_admin)})")
        logging.info(f"  DB is_superadmin value: {user.is_superadmin} (type: {type(user.is_superadmin)})")
        logging.info(f"  Final result: {is_admin}")
        
        return is_admin
        
    except Exception as e:
        logging.error(f"Error in check_admin: {e}", exc_info=True)
        return False 