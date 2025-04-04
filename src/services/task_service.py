from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy import select, delete, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
from src.database.models import Task, TaskAssignment, Submission, User
from src.database.models.task import TaskStatus
from sqlalchemy.types import Date
import logging

class TaskService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_task(
        self, 
        press_release_link: str, 
        deadline: datetime,
        created_by: int,
        photo: Optional[str] = None
    ) -> Task:
        task = Task(
            press_release_link=press_release_link,
            deadline=deadline,
            status='new',
            created_by=created_by,
            photo=photo
        )
        self.session.add(task)
        await self.session.commit()
        await self.session.refresh(task)
        return task

    async def check_media_outlet_submission(self, task_id: int, media_outlet: str) -> bool:
        """Проверяет, есть ли уже одобренная или завершенная публикация от этого СМИ"""
        query = (
            select(Submission)
            .join(User, User.id == Submission.user_id)
            .where(
                and_(
                    Submission.task_id == task_id,
                    User.media_outlet == media_outlet,
                    Submission.status.in_(['approved', 'completed'])
                )
            )
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None

    async def assign_task(self, task_id: int, media_outlet: str) -> Optional[TaskAssignment]:
        # Проверяем, не назначено ли задание уже другому представителю того же СМИ
        existing_assignment = await self.get_task_assignment(task_id, media_outlet)
        if existing_assignment:
            return None  # Задание уже назначено представителю этого СМИ
            
        # Проверяем, нет ли уже одобренной публикации от этого СМИ
        has_completed_submission = await self.check_media_outlet_submission(task_id, media_outlet)
        if has_completed_submission:
            return None  # Задание уже выполнено этим СМИ
        
        assignment = TaskAssignment(
            task_id=task_id,
            media_outlet=media_outlet,
            status='in_progress'
        )
        self.session.add(assignment)
        
        task_query = select(Task).where(Task.id == task_id)
        task_result = await self.session.execute(task_query)
        task = task_result.scalar_one()
        task.status = 'in_progress'
        
        await self.session.commit()
        await self.session.refresh(assignment)
        return assignment

    async def get_active_tasks(self, media_outlet: str = None) -> List[Task]:
        """Получает активные задания, которые можно взять в работу или уже взяты данным СМИ"""
        now = datetime.utcnow()
        
        # Базовый запрос для заданий, не просроченных по дедлайну
        query = select(Task).where(Task.deadline >= now)
        
        if media_outlet:
            # Подзапрос для получения ID заданий, которые уже выполнены этим СМИ
            completed_tasks_subquery = (
                select(Submission.task_id)
                .join(User, User.id == Submission.user_id)
                .where(
                    and_(
                        User.media_outlet == media_outlet,
                        Submission.status.in_(['approved', 'completed'])
                    )
                )
            )
            
            # Подзапрос для получения ID заданий, которые взяты в работу этим СМИ
            assignments_subquery = (
                select(TaskAssignment.task_id)
                .where(TaskAssignment.media_outlet == media_outlet)
            )
            
            # Получаем задания, которые:
            # 1. Либо новые И не выполнены этим СМИ
            # 2. Либо взяты в работу этим СМИ И не выполнены
            query = query.where(
                and_(
                    Task.id.notin_(completed_tasks_subquery),  # Исключаем выполненные задания
                    or_(
                        Task.status == TaskStatus.NEW,  # Новые задания
                        Task.id.in_(assignments_subquery)  # Задания этого СМИ
                    )
                )
            )
        else:
            # Если СМИ не указано, показываем только новые задания
            query = query.where(Task.status == TaskStatus.NEW)
        
        query = query.order_by(Task.created_at.desc())
        
        result = await self.session.execute(query)
        tasks = result.scalars().all()
        
        for task in tasks:
            logging.info(f"Task {task.id}: photo={task.photo}")
        
        return tasks

    async def check_task_assignment(self, task_id: int, media_outlet: str) -> bool:
        query = select(TaskAssignment).where(
            TaskAssignment.task_id == task_id,
            TaskAssignment.media_outlet == media_outlet
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none() is not None

    async def get_task_assignment(self, task_id: int, media_outlet: str) -> Optional[TaskAssignment]:
        query = select(TaskAssignment).where(
            TaskAssignment.task_id == task_id,
            TaskAssignment.media_outlet == media_outlet
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def get_task_by_id(self, task_id: int) -> Optional[Task]:
        """Получает задание по его ID"""
        query = select(Task).where(Task.id == task_id)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def is_task_taken_by_user(self, task_id: int, user_id: int) -> bool:
        """Проверяет, взято ли задание уже этим пользователем"""
        query = (
            select(TaskAssignment)
            .where(TaskAssignment.task_id == task_id)
            .where(TaskAssignment.user_id == user_id)
        )
        result = await self.session.execute(query)
        return result.scalar() is not None

    async def delete_task_with_related_data(self, task_id: int):
        # Удаляем все связанные публикации
        await self.session.execute(
            delete(Submission)
            .where(Submission.task_id == task_id)
        )
        
        # Удаляем все назначения
        await self.session.execute(
            delete(TaskAssignment)
            .where(TaskAssignment.task_id == task_id)
        )
        
        # Удаляем само задание
        await self.session.execute(
            delete(Task)
            .where(Task.id == task_id)
        )
        
        await self.session.commit()

    async def get_all_tasks(self) -> List[Task]:
        """Получает все задания"""
        query = select(Task).order_by(Task.created_at.desc())
        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_user_submission_for_task(self, user_id: int, task_id: int) -> Optional[Submission]:
        """Получает публикацию пользователя для конкретного задания"""
        query = (
            select(Submission)
            .where(Submission.user_id == user_id)
            .where(Submission.task_id == task_id)
            .options(joinedload(Submission.user))
        )
        result = await self.session.execute(query)
        return result.scalar_one_or_none()