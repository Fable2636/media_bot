from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
from src.database.models import Submission, Task, TaskAssignment
import logging
from src.services.task_service import TaskService


class SubmissionService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_submission(
        self, 
        task_id: int, 
        user_id: int, 
        content: str, 
        photo: str = None
    ) -> Optional[Submission]:
        # Проверяем, существует ли задание
        task_service = TaskService(self.session)
        task = await task_service.get_task_by_id(task_id)
        
        if not task:
            return None  # Задание не существует
        
        submission = Submission(
            task_id=task_id,
            user_id=user_id,
            content=content,
            photo=photo,
            submitted_at=datetime.now(),
            status='pending'
        )
        self.session.add(submission)
        await self.session.commit()
        await self.session.refresh(submission)
        return submission

    async def get_pending_submissions(self) -> List[Submission]:
        query = (
            select(Submission)
            .options(joinedload(Submission.user))
            .where(Submission.status == 'pending')
            .order_by(Submission.submitted_at.desc())
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def approve_submission(self, submission_id: int) -> Submission:
        logging.info(f"Approving submission {submission_id}")
        submission = await self.session.get(Submission, submission_id)
        if not submission:
            raise ValueError(f"Submission with id {submission_id} not found")

        submission.status = 'approved'
        await self.session.commit()
        await self.session.refresh(submission)
        logging.info(f"Submission {submission_id} approved")
        return submission

    async def request_revision(self, submission_id: int, comment: str) -> Submission:
        query = select(Submission).where(Submission.id == submission_id)
        result = await self.session.execute(query)
        submission = result.scalar_one()
        
        submission.status = 'revision'
        submission.revision_comment = comment
        await self.session.commit()
        return submission

    async def add_published_link(
        self, 
        submission_id: int, 
        published_link: str
    ) -> Submission:
        try:
            # Получаем публикацию
            submission = await self.session.get(Submission, submission_id)
            if not submission:
                raise ValueError(f"Submission with id {submission_id} not found")

            # Обновляем статус и ссылку
            submission.status = 'completed'
            submission.published_link = published_link

            # Сохраняем изменения
            await self.session.commit()
            await self.session.refresh(submission)

            return submission

        except Exception as e:
            await self.session.rollback()
            raise e

    async def get_user_submissions(self, user_id: int, active_only: bool = True) -> List[Submission]:
        now = datetime.now()
        query = (
            select(Submission)
            .options(joinedload(Submission.user))
            .where(Submission.user_id == user_id)
        )
        
        if active_only:
            # Фильтруем активные публикации ИЛИ сделанные за последние сутки
            query = query.where(
                or_(
                    Submission.status.in_(['pending', 'revision']),
                    Submission.submitted_at >= now - timedelta(days=1)
                )
            )
        
        query = query.order_by(Submission.submitted_at.desc())
        
        result = await self.session.execute(query)
        return result.scalars().all()

    async def update_submission_content(
        self, 
        submission_id: int, 
        content: str, 
        photo: str = None
    ) -> Submission:
        submission = await self.session.get(Submission, submission_id)
        if submission:
            submission.content = content
            submission.photo = photo
            submission.status = 'pending'
            await self.session.commit()
            await self.session.refresh(submission)
        return submission

    async def get_submission_with_user(self, submission_id: int) -> Submission:
        """Получает публикацию вместе с данными пользователя"""
        query = (
            select(Submission)
            .options(joinedload(Submission.user))
            .where(Submission.id == submission_id)
        )
        result = await self.session.execute(query)
        return result.scalar_one()

    async def get_submission(self, submission_id: int) -> Submission:
        """Получает публикацию по ID"""
        query = select(Submission).where(Submission.id == submission_id)
        result = await self.session.execute(query)
        return result.scalar()

    async def get_user_submission_for_task(self, user_id: int, task_id: int) -> Optional[Submission]:
        """Получает публикацию пользователя для конкретного задания"""
        query = (
            select(Submission)
            .where(Submission.user_id == user_id)
            .where(Submission.task_id == task_id)
        )
        result = await self.session.execute(query)
        return result.scalar()