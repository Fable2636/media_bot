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
        # Проверяем флаги в базе данных
        is_admin = bool(user.is_admin)
        is_superadmin = bool(user.is_superadmin)
        
        # Пользователь должен быть либо суперадмином, либо обычным админом
        has_admin_rights = is_superadmin or is_admin
        
        logging.info(f"Admin check for user {user.telegram_id}:")
        logging.info(f"  DB is_admin value: {user.is_admin} (type: {type(user.is_admin)})")
        logging.info(f"  DB is_superadmin value: {user.is_superadmin} (type: {type(user.is_superadmin)})")
        logging.info(f"  Final result: {has_admin_rights}")
        
        return has_admin_rights
        
    except Exception as e:
        logging.error(f"Error in check_admin: {e}", exc_info=True)
        return False 