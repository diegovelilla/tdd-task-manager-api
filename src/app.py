from typing import Annotated, Iterable

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .model import Base, Task

app = FastAPI()

SQLITE_URL = "sqlite:///tasks.db"

engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


# Task Model
class InputTask(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: Annotated[str, Field(max_length=50)]
    completed: bool = False


class OutputTask(BaseModel):
    id: Annotated[int, Field(gt=0)]
    title: Annotated[str, Field(max_length=50)]
    completed: bool = False


def get_db() -> Iterable[Session] | None:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/", status_code=200)
def read_root() -> dict:
    return {"message": "Server is running!"}


@app.get("/tasks/{task_id}", status_code=200)
def get_task(task_id: Annotated[int, Field(gt=0)], db: Session = Depends(get_db)) -> OutputTask:
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=204, detail=f"Unable to find task {task_id}")
    return OutputTask(**task.to_dict())


@app.delete("/tasks/{task_id}", status_code=202)
def delete_task(task_id: Annotated[int, Field(gt=0)], db: Session = Depends(get_db)) -> OutputTask:
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} does not exist.")
    db.delete(task)
    db.commit()
    return OutputTask(**task.to_dict())


@app.post("/tasks/", status_code=201)
def create_task(task: InputTask, db: Session = Depends(get_db)) -> OutputTask:
    title = task.title
    completed = task.completed
    if not title:
        raise HTTPException(status_code=400, detail="Title is required.")
    new_task = Task(title=title, completed=completed)
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return OutputTask(**new_task.to_dict())


@app.get("/tasks/", status_code=200)
def get_tasks(db: Session = Depends(get_db)) -> list:
    tasks = db.query(Task).all()
    return [{"id": task.id, "title": task.title, "completed": task.completed} for task in tasks]
