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
        # Проверяем, существует ли пользователь
        if not user:
            logging.error("check_admin: user объект отсутствует (None)")
            return False
            
        # Логируем подробную информацию о пользователе
        logging.info(f"check_admin подробная информация о пользователе:")
        logging.info(f"  ID в БД: {user.id}")
        logging.info(f"  telegram_id: {user.telegram_id} (тип: {type(user.telegram_id)})")
        logging.info(f"  username: {user.username}")
        logging.info(f"  is_admin значение: {user.is_admin} (тип: {type(user.is_admin)})")
        logging.info(f"  is_superadmin значение: {user.is_superadmin} (тип: {type(user.is_superadmin)})")
        
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