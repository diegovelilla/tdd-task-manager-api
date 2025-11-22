from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, declarative_base, mapped_column

Base = declarative_base()


class Task(Base):
    __tablename__ = "task"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(String(50), nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)

    def __repr__(self) -> str:
        return f"Task(id: {self.id}, title: '{self.title}', completed: {self.completed})"
