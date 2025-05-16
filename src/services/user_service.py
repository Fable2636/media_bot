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
        logging.info(f"🔍 Запрос пользователя с ID {user_id}")
        try:
            query = select(User).where(User.id == user_id)
            logging.info(f"🔍 SQL-запрос: {str(query)}")
            
            result = await self.session.execute(query)
            user = result.scalar_one_or_none()
            
            if user:
                logging.info(f"✅ Найден пользователь: id={user.id}, telegram_id={user.telegram_id}, username={user.username}, is_admin={user.is_admin}")
                
                # Проверка типов данных
                logging.info(f"🔍 Типы данных: telegram_id: {type(user.telegram_id)}, is_admin: {type(user.is_admin)}")
                
                # Проверяем, что telegram_id может быть преобразован в int
                if user.telegram_id:
                    try:
                        telegram_id_int = int(user.telegram_id)
                        logging.info(f"✅ telegram_id успешно конвертируется в int: {telegram_id_int}")
                    except (ValueError, TypeError) as e:
                        logging.error(f"❌ Ошибка преобразования telegram_id в int: {e}")
            else:
                logging.warning(f"⚠️ Пользователь с ID={user_id} не найден в базе данных")
                
            return user
            
        except Exception as e:
            logging.error(f"❌ Ошибка при получении пользователя: {e}", exc_info=True)
            return None

    async def get_all_media_outlets(self) -> List[User]:
        query = select(User).where(User.is_admin == False)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_all_admins(self) -> List[User]:
        """Получает список всех администраторов из базы данных"""
        logging.info("Запрос всех администраторов из базы данных")
        
        try:
            # Используем сырой SQL-запрос для диагностики
            raw_result = await self.session.execute(
                text("SELECT id, telegram_id, username, is_admin, is_superadmin, media_outlet FROM users WHERE is_admin = 1 OR is_admin = 'true' OR is_admin = 't'")
            )
            raw_admins = raw_result.fetchall()
            logging.info(f"Найдено {len(raw_admins)} администраторов через сырой SQL запрос")
            
            # Выводим информацию о каждом администраторе из результатов
            admin_ids = []
            for admin_row in raw_admins:
                try:
                    admin_id = admin_row[0]
                    admin_ids.append(admin_id)
                    logging.info(f"SQL данные админа: id={admin_row[0]}, telegram_id={admin_row[1]}, username={admin_row[2]}, is_admin={admin_row[3]}, is_superadmin={admin_row[4]}")
                except Exception as e:
                    logging.error(f"Ошибка при обработке данных админа: {e}")
            
            # Затем получаем через ORM
            query = select(User).where(User.is_admin == True)
            result = await self.session.execute(query)
            admins = result.scalars().all()
            
            logging.info(f"Через ORM найдено {len(admins)} администраторов")
            
            # Проверяем, всех ли администраторов получили через ORM
            orm_admin_ids = [admin.id for admin in admins]
            missing_admins = set(admin_ids) - set(orm_admin_ids)
            if missing_admins:
                logging.warning(f"Не все администраторы получены через ORM! Отсутствуют ID: {missing_admins}")
            
            return admins
            
        except Exception as e:
            logging.error(f"Ошибка при получении списка администраторов: {e}", exc_info=True)
            return []

    async def get_superadmins(self) -> List[User]:
        """Получает список всех суперадминов из базы данных"""
        logging.info("Запрос всех суперадминов из базы данных")
        
        try:
            # Используем сырой SQL-запрос для диагностики и надежной выборки
            raw_result = await self.session.execute(
                text("SELECT id, telegram_id, username, is_admin, is_superadmin, media_outlet FROM users WHERE is_superadmin = 1 OR is_superadmin = 'true' OR is_superadmin = 't'")
            )
            raw_superadmins = raw_result.fetchall()
            logging.info(f"Найдено {len(raw_superadmins)} суперадминов через сырой SQL запрос")
            
            # Затем получаем через ORM для использования
            query = select(User).where(User.is_superadmin == True)
            result = await self.session.execute(query)
            superadmins = result.scalars().all()
            
            logging.info(f"Через ORM найдено {len(superadmins)} суперадминов")
            
            return superadmins
            
        except Exception as e:
            logging.error(f"Ошибка при получении списка суперадминов: {e}", exc_info=True)
            return []

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