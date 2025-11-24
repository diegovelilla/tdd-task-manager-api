from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, declarative_base, mapped_column, relationship

Base = declarative_base()


# ---------- Database Models ----------
class TaskDB(Base):
    __tablename__ = "task"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(50), nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)

    user = relationship("UserDB", back_populates="tasks")

    def __repr__(self) -> str:
        return f"Task(id: {self.id}, title: '{self.title}', completed: {self.completed}, user_id: {self.user_id})"

    def to_dict(self) -> dict:
        return {"id": self.id, "title": self.title, "completed": self.completed, "user_id": self.user_id}


class UserDB(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)

    tasks = relationship("TaskDB", back_populates="user", cascade="all, delete-orphan")
    api_keys = relationship("ApiKeyDB", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"User(id: {self.id}, email: '{self.email}')"

    def to_dict(self) -> dict:
        return {"id": self.id, "email": self.email}


class ApiKeyDB(Base):
    __tablename__ = "api_key"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False, index=True)
    hashed_key: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    user = relationship("UserDB", back_populates="api_keys")


# ---------- Data Models ----------
class BaseTask(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Annotated[str, Field(max_length=50)]
    completed: bool = False
    user_id: Annotated[int, Field(gt=0)]


class InputTask(BaseTask):
    pass


class OutputTask(BaseTask):
    id: Annotated[int, Field(gt=0)]


class LoginInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: Annotated[str, Field(max_length=254, pattern=r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")]
    password: Annotated[str, Field(min_length=7)]
