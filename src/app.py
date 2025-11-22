from typing import Iterable

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .model import Base, Task

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
def get_task(task_id: int, db: Session = Depends(get_db)) -> dict:
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Unable to find task {task_id}")
    return {"id": task.id, "title": task.title, "completed": task.completed}


@app.post("/tasks/", status_code=201)
def create_task(data: dict, db: Session = Depends(get_db)) -> dict:
    title = data.get("title")
    completed = data.get("completed", False)
    if not title:
        raise HTTPException(status_code=400, detail="Title is required.")
    new_task = Task(title=title, completed=completed)
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return {"id": new_task.id, "title": new_task.title, "completed": new_task.completed}


@app.get("/tasks/", status_code=200)
def get_tasks(db: Session = Depends(get_db)) -> list:
    tasks = db.query(Task).all()
    return [{"id": task.id, "title": task.title, "completed": task.completed} for task in tasks]
