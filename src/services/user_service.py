from typing import Optional, List
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.models import User
import logging

class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        query = select(User).where(User.telegram_id == telegram_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Получает пользователя по его внутреннему ID в базе данных"""
        logging.info(f"Запрос пользователя с ID {user_id}")
        query = select(User).where(User.id == user_id)
        result = await self.session.execute(query)
        user = result.scalar_one_or_none()
        if user:
            logging.info(f"Найден пользователь: id={user.id}, telegram_id={user.telegram_id}, "
                       f"username={user.username}, is_admin={user.is_admin}")
        else:
            logging.warning(f"Пользователь с ID {user_id} не найден")
        return user

    async def get_all_media_outlets(self) -> List[User]:
        query = select(User).where(User.is_admin == False)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_all_admins(self) -> List[User]:
        """Получает список всех администраторов из базы данных"""
        logging.info("Запрос всех администраторов из базы данных")
        
        # Используем сырой SQL-запрос для диагностики
        raw_result = await self.session.execute(
            text("SELECT id, telegram_id, username, is_admin, is_superadmin FROM users WHERE is_admin = 1 OR is_admin = 'true' OR is_admin = 't'")
        )
        raw_admins = raw_result.fetchall()
        logging.info(f"Найдено {len(raw_admins)} администраторов через сырой SQL запрос")
        for admin_row in raw_admins:
            logging.info(f"SQL данные админа: id={admin_row[0]}, telegram_id={admin_row[1]}, "
                       f"username={admin_row[2]}, is_admin={admin_row[3]}, is_superadmin={admin_row[4]}")
        
        # Используем стандартный ORM-запрос
        query = select(User).where(User.is_admin == True)
        result = await self.session.execute(query)
        admins = result.scalars().all()
        
        logging.info(f"Найдено {len(admins)} администраторов через ORM")
        for admin in admins:
            logging.info(f"Админ: id={admin.id}, telegram_id={admin.telegram_id}, "
                       f"username={admin.username}, is_admin={admin.is_admin} (тип: {type(admin.is_admin)}), "
                       f"is_superadmin={admin.is_superadmin} (тип: {type(admin.is_superadmin)})")
            
            # Проверка конвертации в bool для диагностики
            is_admin_bool = bool(admin.is_admin)
            logging.info(f"  is_admin после преобразования в bool: {is_admin_bool}")
            
        # Если ORM не находит админов, но SQL находит, создаем объекты вручную
        if len(admins) == 0 and len(raw_admins) > 0:
            logging.warning("ORM запрос не нашел админов, создаем объекты вручную из SQL результатов")
            manual_admins = []
            for admin_row in raw_admins:
                user = User()
                user.id = admin_row[0]
                user.telegram_id = admin_row[1]
                user.username = admin_row[2]
                user.is_admin = True  # Явно устанавливаем True
                user.is_superadmin = bool(admin_row[4]) if admin_row[4] is not None else False
                manual_admins.append(user)
                logging.info(f"Создан объект админа вручную: id={user.id}, telegram_id={user.telegram_id}, "
                           f"username={user.username}, is_admin={user.is_admin}")
            return manual_admins
            
        return admins

    async def create_user(self, telegram_id: int, username: str, 
                         is_admin: bool = False, media_outlet: str = None) -> User:
        user = User(
            telegram_id=telegram_id,
            username=username,
            is_admin=is_admin,
            media_outlet=media_outlet
        )
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user