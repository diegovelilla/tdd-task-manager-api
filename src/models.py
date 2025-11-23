from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, declarative_base, mapped_column

Base = declarative_base()


# Database Models
class TaskDB(Base):
    __tablename__ = "task"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(50), nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)

    def __repr__(self) -> str:
        return f"Task(id: {self.id}, title: '{self.title}', completed: {self.completed})"

    def to_dict(self) -> dict:
        return {"id": self.id, "title": self.title, "completed": self.completed}


# Data Models
class BaseTask(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: Annotated[str, Field(max_length=50)]
    completed: bool = False


class InputTask(BaseTask):
    pass


class OutputTask(BaseTask):
    id: Annotated[int, Field(gt=0)]
