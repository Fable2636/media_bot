from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.models import User

class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        query = select(User).where(User.telegram_id == telegram_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_all_media_outlets(self) -> List[User]:
        query = select(User).where(User.is_admin == False)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_all_admins(self) -> List[User]:
        """Получает список всех администраторов из базы данных"""
        query = select(User).where(User.is_admin == True)
        result = await self.session.execute(query)
        return result.scalars().all()

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