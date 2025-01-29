from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from src.database.base import Base


class Submission(Base):
    __tablename__ = 'submissions'

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey('tasks.id'))
    user_id = Column(Integer, ForeignKey('users.id'))
    content = Column(Text)
    photo = Column(String, nullable=True)
    submitted_at = Column(DateTime, default=datetime.now)
    status = Column(String, default="pending")
    revision_comment = Column(Text, nullable=True)
    published_link = Column(String, nullable=True)

    task = relationship('Task', back_populates='submissions')
    user = relationship('User', back_populates='submissions')

    def __repr__(self):
        return f"<Submission {self.id} - Task {self.task_id}>"