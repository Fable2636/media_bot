import pandas as pd
from typing import List
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
from src.database.models import Task, Submission, User, TaskAssignment
from src.database.models.task import TaskStatus, SubmissionStatus
import logging

class ExportService:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _get_readable_task_status(self, status: str) -> str:
        status_map = {
            TaskStatus.NEW: 'Новое',
            TaskStatus.IN_PROGRESS: 'В работе',
            TaskStatus.COMPLETED: 'Завершено',
            TaskStatus.EXPIRED: 'Просрочено',
            TaskStatus.CANCELLED: 'Отменено'
        }
        return status_map.get(status, status)

    def _get_readable_submission_status(self, status: str) -> str:
        status_map = {
            'pending': 'На проверке',
            'approved': 'Одобрено',
            'revision': 'На доработке',
            'completed': 'Завершено'
        }
        return status_map.get(status, status)

    async def export_task_report(self, task_id: int) -> str:
        try:
            # Получаем задание
            result = await self.session.execute(
                select(Task).where(Task.id == task_id)
            )
            task = result.scalar_one()
            
            # Получаем все назначения для задания с загрузкой связей
            assignments_result = await self.session.execute(
                select(TaskAssignment).where(TaskAssignment.task_id == task_id)
            )
            assignments = assignments_result.scalars().all()
            
            # Получаем все публикации для задания с предзагрузкой пользователей
            result = await self.session.execute(
                select(Submission)
                .options(joinedload(Submission.user))  # Предзагружаем связанного пользователя
                .where(Submission.task_id == task_id)
            )
            submissions = result.scalars().all()
            
            # Создаем данные для Excel
            submissions_data = []
            for submission in submissions:
                submissions_data.append({
                    'ID публикации': submission.id,
                    'СМИ': submission.user.media_outlet,
                    'Статус публикации': self._get_readable_submission_status(submission.status),
                    'Дата отправки': submission.submitted_at.strftime('%d.%m.%Y %H:%M'),
                    'Текст': submission.content,
                    'Комментарий': submission.revision_comment,
                    'Ссылка на публикацию': submission.published_link
                })
            
            # Создаем данные о статусе выполнения для каждого СМИ
            assignments_data = []
            for assignment in assignments:
                assignments_data.append({
                    'СМИ': assignment.media_outlet,
                    'Статус выполнения': '✅ Завершено' if assignment.status == 'completed' else '🔄 В работе',
                    'Дата назначения': assignment.assigned_at.strftime('%d.%m.%Y %H:%M')
                })
            
            # Создаем DataFrame
            submissions_df = pd.DataFrame(submissions_data)
            assignments_df = pd.DataFrame(assignments_data)
            
            # Добавляем информацию о задании
            task_info = pd.DataFrame([{
                'ID задания': task.id,
                'Пресс-релиз': task.press_release_link,
                'Дедлайн': task.deadline.strftime('%d.%m.%Y %H:%M'),
                'Статус': self._get_readable_task_status(task.status),
                'Дата создания': task.created_at.strftime('%d.%m.%Y %H:%M')
            }])
            
            # Формируем имя файла
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"task_{task_id}_report_{timestamp}.xlsx"
            
            # Создаем Excel writer
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                task_info.to_excel(writer, sheet_name='Информация о задании', index=False)
                assignments_df.to_excel(writer, sheet_name='Статусы по СМИ', index=False)
                if not submissions_data:
                    pd.DataFrame({'Статус': ['Нет публикаций']}).to_excel(writer, sheet_name='Публикации', index=False)
                else:
                    submissions_df.to_excel(writer, sheet_name='Публикации', index=False)
            
            logging.info(f"Report created: {filename}")
            logging.info(f"Task info: {task_info.to_dict()}")
            logging.info(f"Submissions data: {submissions_data}")
            
            return filename
            
        except Exception as e:
            logging.error(f"Error creating report: {e}", exc_info=True)
            raise

    async def export_all_tasks_report(self) -> str:
        try:
            # Получаем все задания
            tasks_result = await self.session.execute(
                select(Task).order_by(Task.created_at.desc())
            )
            tasks = tasks_result.scalars().all()
            
            all_submissions_data = []
            all_assignments_data = []
            all_tasks_data = []
            
            for task in tasks:
                # Добавляем информацию о задании
                all_tasks_data.append({
                    'ID задания': task.id,
                    'Пресс-релиз': task.press_release_link,
                    'Дедлайн': task.deadline.strftime('%d.%m.%Y %H:%M'),
                    'Статус': self._get_readable_task_status(task.status),
                    'Дата создания': task.created_at.strftime('%d.%m.%Y %H:%M')
                })
                
                # Получаем назначения для задания с информацией о пользователе
                assignments_result = await self.session.execute(
                    select(TaskAssignment, User)
                    .select_from(TaskAssignment)
                    .join(
                        Submission,
                        (Submission.task_id == TaskAssignment.task_id) &
                        (Submission.user_id == User.id)
                    )
                    .join(
                        User,
                        User.media_outlet == TaskAssignment.media_outlet
                    )
                    .where(TaskAssignment.task_id == task.id)
                    .group_by(TaskAssignment.id, User.id)
                )
                assignments = assignments_result.all()
                
                for assignment, user in assignments:
                    all_assignments_data.append({
                        'ID задания': task.id,
                        'СМИ': assignment.media_outlet,
                        'ID пользователя': user.telegram_id,
                        'Имя пользователя': user.username,
                        'Статус выполнения': '✅ Завершено' if assignment.status == 'completed' else '🔄 В работе',
                        'Дата назначения': assignment.assigned_at.strftime('%d.%m.%Y %H:%M')
                    })
                
                # Получаем публикации для задания
                submissions_result = await self.session.execute(
                    select(Submission)
                    .options(joinedload(Submission.user))
                    .where(Submission.task_id == task.id)
                )
                submissions = submissions_result.scalars().all()
                
                for submission in submissions:
                    all_submissions_data.append({
                        'ID задания': task.id,
                        'ID публикации': submission.id,
                        'СМИ': submission.user.media_outlet,
                        'Статус публикации': self._get_readable_submission_status(submission.status),
                        'Дата отправки': submission.submitted_at.strftime('%d.%m.%Y %H:%M'),
                        'Текст': submission.content,
                        'Комментарий к доработке': submission.revision_comment or '',
                        'Ссылка на публикацию': submission.published_link or ''
                    })
            
            # Создаем DataFrame для каждого типа данных
            tasks_df = pd.DataFrame(all_tasks_data)
            assignments_df = pd.DataFrame(all_assignments_data)
            submissions_df = pd.DataFrame(all_submissions_data)
            
            # Формируем имя файла
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"all_tasks_report_{timestamp}.xlsx"
            
            # Создаем Excel writer
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                tasks_df.to_excel(writer, sheet_name='Задания', index=False)
                assignments_df.to_excel(writer, sheet_name='Назначения', index=False)
                if not all_submissions_data:
                    pd.DataFrame({'Статус': ['Нет публикаций']}).to_excel(writer, sheet_name='Публикации', index=False)
                else:
                    submissions_df.to_excel(writer, sheet_name='Публикации', index=False)
            
            logging.info(f"Report created: {filename}")
            return filename
            
        except Exception as e:
            logging.error(f"Error creating report: {e}", exc_info=True)
            raise

    async def export_submissions_to_excel(self, task_id: int) -> str:
        try:
            # Получаем все публикации для задания
            query = (
                select(Submission)
                .options(joinedload(Submission.user))
                .where(Submission.task_id == task_id)
            )
            result = await self.session.execute(query)
            submissions = result.scalars().all()

            if not submissions:
                raise ValueError("No submissions found for the task")

            # Создаем DataFrame
            data = []
            for submission in submissions:
                data.append({
                    "ID": submission.id,
                    "Пользователь": submission.user.username,
                    "Содержание": submission.content,
                    "Статус": submission.status,
                    "Дата отправки": submission.submitted_at.strftime("%Y-%m-%d %H:%M:%S"),
                    "Комментарий к доработке": submission.revision_comment,
                    "Ссылка на публикацию": submission.published_link
                })

            df = pd.DataFrame(data)

            # Сохраняем в Excel
            filename = f"submissions_task_{task_id}.xlsx"
            df.to_excel(filename, index=False)

            return filename

        except Exception as e:
            logging.error(f"Error exporting submissions to Excel: {e}")
            raise