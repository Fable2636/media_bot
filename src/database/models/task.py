from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from src.database.base import Base

class TaskStatus:
    NEW = 'new'              # Новое задание, только что создано
    IN_PROGRESS = 'in_progress'  # Задание в работе (есть хотя бы одна публикация)
    COMPLETED = 'completed'   # Все публикации одобрены
    EXPIRED = 'expired'      # Прошел дедлайн
    CANCELLED = 'cancelled'  # Задание отменено

class SubmissionStatus:
    DRAFT = 'draft'          # Черновик публикации
    PENDING = 'pending'      # Ожидает проверки админом
    REVISION = 'revision'    # Отправлено на доработку
    APPROVED = 'approved'    # Публикация одобрена
    REJECTED = 'rejected'    # Публикация отклонена

class Task(Base):
    __tablename__ = 'tasks'

    id = Column(Integer, primary_key=True)
    press_release_link = Column(String, nullable=False)
    deadline = Column(DateTime, nullable=False)
    status = Column(String, nullable=False, default=TaskStatus.NEW)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    photo = Column(String, nullable=True)

    assigned_media = relationship('TaskAssignment', back_populates='task')
    submissions = relationship('Submission', back_populates='task')
    creator = relationship("User", back_populates="created_tasks")

    def __repr__(self):
        return f"<Task {self.id} ({self.status})>"