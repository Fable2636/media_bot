from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime
from src.database.base import Base

class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"))
    user_id = Column(Integer, ForeignKey("users.id"))
    content = Column(Text)
    photo = Column(String, nullable=True)
    submitted_at = Column(DateTime, default=datetime.now)
    status = Column(String, default="pending")
    revision_comment = Column(Text, nullable=True)
    published_link = Column(String, nullable=True)

    task = relationship("Task", back_populates="submissions")
    user = relationship("User", back_populates="submissions")

class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True)
    press_release_link = Column(String)
    deadline = Column(DateTime)
    status = Column(String, default="new")
    created_at = Column(DateTime, default=datetime.now)
    created_by = Column(Integer, ForeignKey("users.id"))
    photo = Column(String, nullable=True)

    submissions = relationship("Submission", back_populates="task") 