from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
from src.database.models import Submission, Task, TaskAssignment
from src.database.models.submission import SubmissionStatus
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
            
        # Проверяем, нет ли уже публикации от этого пользователя для данного задания
        existing_submission = await self.get_user_submission_for_task(user_id, task_id)
        if existing_submission:
            logging.error(f"User {user_id} already has a submission for task {task_id}")
            return None  # У пользователя уже есть публикация для этого задания
        
        submission = Submission(
            task_id=task_id,
            user_id=user_id,
            content=content,
            photo=photo,
            submitted_at=datetime.now(),
            status=SubmissionStatus.PENDING.value
        )
        self.session.add(submission)
        await self.session.commit()
        await self.session.refresh(submission)
        return submission

    async def get_pending_submissions(self) -> List[Submission]:
        """Получает публикации, требующие действий от администратора"""
        query = (
            select(Submission)
            .options(joinedload(Submission.user))
            .where(
                Submission.status.in_([
                    SubmissionStatus.PENDING.value,
                    SubmissionStatus.PHOTO_PENDING.value
                ])
            )
            .order_by(Submission.submitted_at.desc())
        )
        result = await self.session.execute(query)
        return result.scalars().all()

    async def approve_submission(self, submission_id: int) -> Submission:
        """Одобряет публикацию"""
        submission = await self.get_submission_with_user(submission_id)
        if not submission:
            raise ValueError(f"Submission with id {submission_id} not found")

        logging.info(f"Approving submission {submission_id}. Current photo: {submission.photo}, Current status: {submission.status}")
        
        # Проверяем, можно ли одобрить публикацию
        if submission.status == SubmissionStatus.APPROVED.value:
            logging.warning(f"Submission {submission_id} is already approved")
            raise ValueError("Публикация уже одобрена")
            
        if submission.status == SubmissionStatus.REVISION.value:
            logging.warning(f"Cannot approve submission {submission_id} while it's in revision")
            raise ValueError("Нельзя одобрить публикацию, которая находится на доработке")
            
        if submission.status == SubmissionStatus.COMPLETED.value:
            logging.warning(f"Cannot approve submission {submission_id} that is already completed")
            raise ValueError("Нельзя одобрить завершенную публикацию")
        
        # Если статус PENDING, значит одобряем текст
        if submission.status == SubmissionStatus.PENDING.value:
            # Устанавливаем статус TEXT_APPROVED независимо от наличия фото
            submission.status = SubmissionStatus.TEXT_APPROVED.value
            logging.info(f"Setting status to TEXT_APPROVED for submission {submission_id}")
        
        # Если статус PHOTO_PENDING, значит одобряем фото
        elif submission.status == SubmissionStatus.PHOTO_PENDING.value:
            submission.status = SubmissionStatus.APPROVED.value
            logging.info(f"Setting status to APPROVED for submission {submission_id}")
        
        await self.session.commit()
        await self.session.refresh(submission)
        logging.info(f"Final status for submission {submission_id}: {submission.status}")
        return submission

    async def request_revision(self, submission_id: int, comment: str, is_photo_revision: bool = False) -> Submission:
        try:
            # Получаем публикацию с данными пользователя
            submission = await self.get_submission_with_user(submission_id)
            if not submission:
                logging.error(f"Submission with id {submission_id} not found")
                raise ValueError(f"Submission with id {submission_id} not found")
            
            logging.info(f"Requesting revision for submission {submission_id}")
            logging.info(f"Current status: {submission.status}, Is photo revision: {is_photo_revision}")
            
            # Проверяем статус публикации
            if submission.status == SubmissionStatus.REVISION.value:
                logging.warning(f"Submission {submission_id} is already in revision")
                raise ValueError("Публикация уже находится на доработке")
                
            if submission.status == SubmissionStatus.COMPLETED.value:
                logging.warning(f"Cannot request revision for completed submission {submission_id}")
                raise ValueError("Нельзя отправить на доработку завершенную публикацию")
                
            if submission.status == SubmissionStatus.APPROVED.value:
                logging.warning(f"Cannot request revision for approved submission {submission_id}")
                raise ValueError("Нельзя отправить на доработку одобренную публикацию")
            
            # Сохраняем предыдущий статус для возврата после доработки
            if is_photo_revision:
                submission.previous_status = SubmissionStatus.TEXT_APPROVED.value
                # Очищаем фото, так как оно требует доработки
                submission.photo = None
            else:
                submission.previous_status = SubmissionStatus.PENDING.value
            
            # Обновляем статус и комментарий
            submission.status = SubmissionStatus.REVISION.value
            submission.revision_comment = comment
            
            await self.session.commit()
            await self.session.refresh(submission)
            
            logging.info(f"Revision requested successfully for submission {submission_id}")
            logging.info(f"Previous status saved: {submission.previous_status}")
            return submission
            
        except Exception as e:
            logging.error(f"Error in request_revision: {e}", exc_info=True)
            await self.session.rollback()
            raise

    async def add_published_link(
        self, 
        submission_id: int, 
        published_link: str
    ) -> Submission:
        try:
            submission = await self.session.get(Submission, submission_id)
            if not submission:
                raise ValueError(f"Submission with id {submission_id} not found")

            submission.status = SubmissionStatus.COMPLETED.value
            submission.published_link = published_link

            await self.session.commit()
            await self.session.refresh(submission)
            return submission

        except Exception as e:
            await self.session.rollback()
            raise e

    async def get_user_submissions(self, user_id: int, active_only: bool = True) -> List[Submission]:
        """Получает публикации пользователя"""
        now = datetime.now()
        query = (
            select(Submission)
            .options(joinedload(Submission.user))
            .where(Submission.user_id == user_id)
        )
        
        if active_only:
            # Фильтруем активные публикации ИЛИ завершенные за последние сутки
            query = query.where(
                or_(
                    Submission.status.in_([
                        SubmissionStatus.PENDING.value,
                        SubmissionStatus.REVISION.value,
                        SubmissionStatus.TEXT_APPROVED.value,
                        SubmissionStatus.PHOTO_PENDING.value,
                        SubmissionStatus.APPROVED.value
                    ]),
                    and_(
                        Submission.status == SubmissionStatus.COMPLETED.value,
                        Submission.submitted_at >= now - timedelta(days=1)
                    )
                )
            )
        else:
            # Для архива показываем только завершенные публикации
            query = query.where(Submission.status == SubmissionStatus.COMPLETED.value)
        
        query = query.order_by(Submission.submitted_at.desc())
        
        result = await self.session.execute(query)
        return result.scalars().all()

    async def update_submission_content(
        self, 
        submission_id: int, 
        content: str = None, 
        photo: str = None
    ) -> Submission:
        """Обновляет содержимое публикации"""
        submission = await self.get_submission(submission_id)
        if submission:
            if content is not None:
                submission.content = content
                # Если публикация была на доработке, возвращаем предыдущий статус
                if submission.status == SubmissionStatus.REVISION.value and submission.previous_status:
                    submission.status = submission.previous_status
                    submission.previous_status = None
                    submission.revision_comment = None
                else:
                    submission.status = SubmissionStatus.PENDING.value
                    
            if photo is not None:
                # Проверяем, что текст уже одобрен или это доработка фото
                if (submission.status == SubmissionStatus.TEXT_APPROVED.value or 
                    (submission.status == SubmissionStatus.REVISION.value and 
                     submission.previous_status == SubmissionStatus.TEXT_APPROVED.value)):
                    submission.photo = photo
                    submission.status = SubmissionStatus.PHOTO_PENDING.value
                    # Если это была доработка, очищаем поля доработки
                    if submission.previous_status:
                        submission.previous_status = None
                        submission.revision_comment = None
                    logging.info(f"Setting status to PHOTO_PENDING for submission {submission_id}")
                else:
                    logging.error(f"Cannot add photo before text is approved. Current status: {submission.status}")
                    raise ValueError("Cannot add photo before text is approved")
            
            await self.session.commit()
            await self.session.refresh(submission)
            logging.info(f"Updated submission {submission_id}. New status: {submission.status}")
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