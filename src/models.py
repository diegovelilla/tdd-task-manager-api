from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, declarative_base, mapped_column

Base = declarative_base()


# Database Models
class TaskDB(Base):
    __tablename__ = "task"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(50), nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))

    def __repr__(self) -> str:
        return f"Task(id: {self.id}, title: '{self.title}', completed: {self.completed}, user_id: {self.user_id})"

    def to_dict(self) -> dict:
        return {"id": self.id, "title": self.title, "completed": self.completed, "user_id": self.user_id}


class UserDB(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    first_name: Mapped[str] = mapped_column(String(20), nullable=False)
    last_name: Mapped[str] = mapped_column(String(20))

    def __repr__(self) -> str:
        return f"User(id: {self.id}, first_name: '{self.first_name}', second_name: {self.last_name})"

    def to_dict(self) -> dict:
        return {"id": self.id, "first_name": self.first_name, "second_name": self.last_name}


# Data Models
class BaseTask(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Annotated[str, Field(max_length=50)]
    completed: bool = False
    user_id: Annotated[int, Field(gt=0)]


class InputTask(BaseTask):
    pass


class OutputTask(BaseTask):
    id: Annotated[int, Field(gt=0)]
