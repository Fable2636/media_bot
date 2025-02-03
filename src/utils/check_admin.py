from src.config.users import ADMINS
from src.database.models import User
import logging

async def check_admin(user: User) -> bool:
    """
    Проверяет, является ли пользователь администратором
    
    Args:
        user (User): Объект пользователя
        
    Returns:
        bool: True если пользователь администратор, False в противном случае
    """
    try:
        # Проверяем, есть ли пользователь в списке администраторов
        is_in_admins = any(admin["telegram_id"] == user.telegram_id for admin in ADMINS)
        
        # Проверяем флаг is_admin в базе данных
        is_admin_in_db = int(user.is_admin) == 1
        
        # Пользователь должен быть и в списке админов, и иметь флаг в базе
        is_admin = is_in_admins and is_admin_in_db
        
        logging.info(f"Admin check for user {user.telegram_id}:")
        logging.info(f"  In ADMINS list: {is_in_admins}")
        logging.info(f"  DB is_admin value: {user.is_admin} (type: {type(user.is_admin)})")
        logging.info(f"  Final result: {is_admin}")
        
        return is_admin
        
    except Exception as e:
        logging.error(f"Error in check_admin: {e}", exc_info=True)
        return False 