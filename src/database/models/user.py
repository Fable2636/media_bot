from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship
from src.database.base import Base


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True)
    username = Column(String, nullable=True)
    is_admin = Column(Boolean, default=False)
    media_outlet = Column(String, nullable=True)

    # Добавляем связь с заданиями
    created_tasks = relationship("Task", back_populates="creator")

    # Добавляем связь с Submission
    submissions = relationship('Submission', back_populates='user')

    def __repr__(self):
        return f"<User {self.id} - {self.username}>"

    def __str__(self):
        return self.__repr__()