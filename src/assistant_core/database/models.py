import datetime
from typing import Optional, Dict, Any

from sqlalchemy import create_engine, Integer, String, DateTime, ForeignKey, Boolean, Text, JSON, func
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Mapped, mapped_column

from common.config import BASE_DIR

Base = declarative_base()


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    access_level: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(200))
    users: Mapped[list["User"]] = relationship(back_populates="role")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    voice_embedding: Mapped[str] = mapped_column(Text, nullable=True)

    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true")

    role: Mapped["Role"] = relationship(back_populates="users")


class Settings(Base):
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    value: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(200))


class Command(Base):
    __tablename__ = "commands"

    id: Mapped[int] = mapped_column(primary_key=True)
    intent_name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    access_level: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255))
    is_async: Mapped[bool] = mapped_column(Boolean, server_default="false")



class ExecutionLog(Base):
    __tablename__ = "execution_logs"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    raw_voice_text: Mapped[Optional[str]] = mapped_column(Text)
    extracted_entities: Mapped[Dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    intent_name: Mapped[str] = mapped_column(String(100), nullable=True)

    status: Mapped[str] = mapped_column(String(50))
    system_response: Mapped[Optional[str]] = mapped_column(Text)

    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, onupdate=func.now(), server_default=func.now())

    user: Mapped["User"] = relationship()


# Инициализация подключения (SQLite для локальной разработки, легко меняется на PostgreSQL)
DATABASE_URL = f"sqlite:///{BASE_DIR}/assistant.db"
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)


def init_db():
    """Создает таблицы, если их нет"""
    Base.metadata.create_all(engine)