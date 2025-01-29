from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from src.database.base import Base


class TaskAssignment(Base):
    __tablename__ = 'task_assignments'

    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey('tasks.id'))
    media_outlet = Column(String)
    assigned_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String)  # in_progress, completed

    task = relationship('Task', back_populates='assigned_media')

    def __repr__(self):
        return f"<TaskAssignment {self.task_id} - {self.media_outlet}>"