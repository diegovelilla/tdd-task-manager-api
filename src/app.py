from typing import Annotated, Iterable

from fastapi import Depends, FastAPI, HTTPException
from pydantic import Field
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base, InputTask, OutputTask, TaskDB

app = FastAPI()

SQLITE_URL = "sqlite:///tasks.db"

engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


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
    task = db.query(TaskDB).filter(TaskDB.id == task_id).first()
    if not task:
        raise HTTPException(status_code=204, detail=f"Unable to find task {task_id}")
    return OutputTask(**task.to_dict())


@app.delete("/tasks/{task_id}", status_code=202)
def delete_task(task_id: Annotated[int, Field(gt=0)], db: Session = Depends(get_db)) -> OutputTask:
    task = db.query(TaskDB).filter(TaskDB.id == task_id).first()
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
    new_task = TaskDB(title=title, completed=completed)
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return OutputTask(**new_task.to_dict())


@app.get("/tasks/", status_code=200)
def get_tasks(db: Session = Depends(get_db)) -> list:
    tasks = db.query(TaskDB).all()
    return [{"id": task.id, "title": task.title, "completed": task.completed} for task in tasks]


@app.put("/tasks/{task_id}", status_code=202)
def update_task(
    task_id: Annotated[int, Field(gt=0)], task: InputTask, db: Session = Depends(get_db)
) -> OutputTask:
    prev_task = db.query(TaskDB).filter(TaskDB.id == task_id).first()
    if not prev_task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} does not exist.")

    for key, value in task.model_dump().items():
        setattr(prev_task, key, value)

    db.commit()
    db.refresh(prev_task)
    return OutputTask(**prev_task.to_dict())
