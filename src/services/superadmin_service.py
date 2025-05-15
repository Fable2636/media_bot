from typing import List, Optional
from sqlalchemy import select, update, delete, text
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.models import User
import logging

class SuperadminService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_admin(self, telegram_id: int, username: str) -> Optional[User]:
        """Добавляет нового администратора"""
        try:
            # Проверяем, существует ли пользователь
            user = await self._get_user_by_telegram_id(telegram_id)
            
            if user:
                # Если пользователь существует, делаем его админом
                user.is_admin = True  # Явно устанавливаем Python bool True
                logging.info(f"Обновляем существующего пользователя: {user.username} (ID: {user.telegram_id})")
                logging.info(f"  Установлено is_admin={user.is_admin} (тип: {type(user.is_admin)})")
                
                # Дополнительно обновляем через SQL для решения проблем с SQLAlchemy/SQLite
                await self.session.execute(
                    text("UPDATE users SET is_admin = 1 WHERE telegram_id = :telegram_id"),
                    {"telegram_id": telegram_id}
                )
                
                user.username = username
                user.media_outlet = None
            else:
                # Создаем нового пользователя-админа
                user = User(
                    telegram_id=telegram_id,
                    username=username,
                    is_admin=True,
                    is_superadmin=False,
                    media_outlet=None
                )
                logging.info(f"Создаем нового админа: {username} (ID: {telegram_id})")
                logging.info(f"  Установлено is_admin={user.is_admin} (тип: {type(user.is_admin)})")
                
                self.session.add(user)
            
            await self.session.commit()
            await self.session.refresh(user)
            
            # Проверяем результат
            logging.info(f"После сохранения в БД: {user.username} (ID: {user.telegram_id})")
            logging.info(f"  Значение is_admin={user.is_admin} (тип: {type(user.is_admin)})")
            
            return user
            
        except Exception as e:
            logging.error(f"Error adding admin: {e}")
            await self.session.rollback()
            raise

    async def remove_admin(self, telegram_id: int) -> bool:
        """Удаляет администратора"""
        try:
            user = await self._get_user_by_telegram_id(telegram_id)
            if not user:
                return False
                
            if user.is_superadmin:
                raise ValueError("Нельзя удалить суперадмина")
                
            user.is_admin = False
            await self.session.commit()
            return True
            
        except Exception as e:
            logging.error(f"Error removing admin: {e}")
            await self.session.rollback()
            raise

    async def add_media_outlet(self, telegram_id: int, username: str, media_outlet: str) -> Optional[User]:
        """Добавляет нового представителя СМИ"""
        try:
            # Проверяем, существует ли пользователь
            user = await self._get_user_by_telegram_id(telegram_id)
            
            if user:
                # Если пользователь существует, обновляем его данные
                user.username = username
                user.media_outlet = media_outlet
                user.is_admin = False
                user.is_superadmin = False
            else:
                # Создаем нового пользователя-СМИ
                user = User(
                    telegram_id=telegram_id,
                    username=username,
                    is_admin=False,
                    is_superadmin=False,
                    media_outlet=media_outlet
                )
                self.session.add(user)
            
            await self.session.commit()
            await self.session.refresh(user)
            return user
            
        except Exception as e:
            logging.error(f"Error adding media outlet: {e}")
            await self.session.rollback()
            raise

    async def remove_media_outlet(self, telegram_id: int) -> bool:
        """Удаляет представителя СМИ"""
        try:
            user = await self._get_user_by_telegram_id(telegram_id)
            if not user or not user.media_outlet:
                return False
                
            await self.session.delete(user)
            await self.session.commit()
            return True
            
        except Exception as e:
            logging.error(f"Error removing media outlet: {e}")
            await self.session.rollback()
            raise

    async def get_all_admins(self) -> List[User]:
        """Получает список всех администраторов"""
        query = select(User).where(User.is_admin == True)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_all_media_outlets(self) -> List[User]:
        """Получает список всех представителей СМИ"""
        query = select(User).where(User.media_outlet.isnot(None))
        result = await self.session.execute(query)
        return result.scalars().all()

    async def _get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Получает пользователя по telegram_id"""
        query = select(User).where(User.telegram_id == telegram_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def toggle_superadmin(self, telegram_id: int) -> Optional[User]:
        """Включает/выключает статус суперадмина для пользователя"""
        try:
            user = await self._get_user_by_telegram_id(telegram_id)
            if not user:
                raise ValueError(f"Пользователь с ID {telegram_id} не найден")
            
            if not user.is_admin:
                raise ValueError("Нельзя сделать суперадмином не-админа")
            
            # Переключаем статус суперадмина
            user.is_superadmin = not user.is_superadmin
            await self.session.commit()
            await self.session.refresh(user)
            return user
            
        except Exception as e:
            logging.error(f"Error toggling superadmin status: {e}")
            await self.session.rollback()
            raise 