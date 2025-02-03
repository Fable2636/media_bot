from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from src.database.base import Base
from enum import Enum


class SubmissionStatus(str, Enum):
    PENDING = 'pending'          # Ожидает проверки текста
    TEXT_APPROVED = 'text_approved'  # Текст одобрен, ожидается фото
    PHOTO_PENDING = 'photo_pending'  # Фото отправлено на проверку
    APPROVED = 'approved'        # Всё одобрено, ожидается ссылка
    REVISION = 'revision'        # Отправлено на доработку
    COMPLETED = 'completed'      # Опубликовано со ссылкой

class Submission(Base):
    __tablename__ = 'submissions'

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey('tasks.id'))
    user_id = Column(Integer, ForeignKey('users.id'))
    content = Column(Text)
    photo = Column(String, nullable=True)
    submitted_at = Column(DateTime, default=datetime.now)
    status = Column(SQLEnum(SubmissionStatus))
    previous_status = Column(SQLEnum(SubmissionStatus), nullable=True)
    revision_comment = Column(Text, nullable=True)
    published_link = Column(String, nullable=True)

    task = relationship('Task', back_populates='submissions')
    user = relationship('User', back_populates='submissions')

    def __repr__(self):
        return f"<Submission {self.id} - Task {self.task_id}>"