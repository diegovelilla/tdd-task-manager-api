from typing import Annotated, Iterable

from fastapi import Depends, FastAPI, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import ExpiredSignatureError, JWTError
from pydantic import Field
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base, InputTask, LoginInput, OutputTask, TaskDB, UserDB
from .utils import create_token, decode_token, hash_pwd, verify_pwd

app = FastAPI()

SQLITE_URL = "sqlite:///tasks.db"

engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

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


@app.post("/login")
def login(data: LoginInput, db: Session = Depends(get_db)) -> dict:
    user = db.query(UserDB).filter(UserDB.email == data.email).first()
    if not user:
        raise HTTPException(status_code=401, detail=f"Unable to find user with email: {data.email}")

    if not verify_pwd(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Wrong password")

    token = create_token(user.id)
    return {"access_token": token, "token_type": "bearer"}


@app.post("/register")
def register(data: LoginInput, db: Session = Depends(get_db)) -> dict:
    if db.query(UserDB).filter(UserDB.email == data.email).first():
        raise HTTPException(status_code=422, detail="Email already registered")
    user = UserDB(email=data.email, password_hash=hash_pwd(data.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_token(user.id)
    return {"access_token": token, "token_type": "bearer"}


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> UserDB:
    try:
        payload = decode_token(token)
        sub = payload.get("sub")
        if not sub:
            raise HTTPException(status_code=401, detail="Invalid token payload")
        user_id = int(sub)
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired", headers={"WWW-Authenticate": "Bearer"})
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token", headers={"WWW-Authenticate": "Bearer"})
    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Error fetching user",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


@app.get("/tasks/{task_id}", status_code=200)
def get_task(
    task_id: Annotated[int, Field(gt=0)],
    user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OutputTask:
    task = db.query(TaskDB).filter(TaskDB.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Unable to find task {task_id}")
    if task.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this task")
    return OutputTask(**task.to_dict())


@app.post("/tasks/", status_code=201)
def create_task(
    task: InputTask, user: UserDB = Depends(get_current_user), db: Session = Depends(get_db)
) -> OutputTask:
    userdb = db.query(UserDB).filter(UserDB.id == task.user_id).first()
    if not userdb:
        raise HTTPException(status_code=422, detail=f"User with id {task.user_id} does not exist")
    if user.id != task.user_id:
        raise HTTPException(status_code=403, detail="Not authorized to create task for this user")
    new_task = TaskDB(**task.model_dump())
    db.add(new_task)
    db.commit()
    db.refresh(new_task)
    return OutputTask(**new_task.to_dict())


@app.delete("/tasks/{task_id}", status_code=202)
def delete_task(
    task_id: Annotated[int, Field(gt=0)],
    user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OutputTask:
    task = db.query(TaskDB).filter(TaskDB.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} does not exist.")
    if task.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this task")
    db.delete(task)
    db.commit()
    return OutputTask(**task.to_dict())


@app.put("/tasks/{task_id}", status_code=202)
def update_task(
    task_id: Annotated[int, Field(gt=0)],
    task: InputTask,
    user: UserDB = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> OutputTask:
    prev_task = db.query(TaskDB).filter(TaskDB.id == task_id).first()
    if not prev_task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} does not exist.")
    if prev_task.user_id != user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this task")

    for key, value in task.model_dump().items():
        setattr(prev_task, key, value)

    db.commit()
    db.refresh(prev_task)
    return OutputTask(**prev_task.to_dict())


@app.get("/tasks/", status_code=200)
def get_tasks(user: UserDB = Depends(get_current_user), db: Session = Depends(get_db)) -> list:
    tasks = db.query(TaskDB).filter(TaskDB.user_id == user.id).all()
    return [OutputTask(**task.to_dict()) for task in tasks]
