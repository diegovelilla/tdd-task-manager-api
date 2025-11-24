import pytest
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import sessionmaker

from src.app import app, get_db
from src.models import Base, InputTask, LoginInput, OutputTask, TaskDB, UserDB
from src.utils import hash_pwd

client = TestClient(app)

TESTING_SQLITE_URL = "sqlite:///:memory:"
engine = create_engine(TESTING_SQLITE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Override the get_db function to work with TestingSessionLocal() instead of SessionLocal()
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Override the get_db function
app.dependency_overrides[get_db] = override_get_db


@pytest.fixture
def setup():
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    user1 = UserDB(id=1, email="test1@gmail.com", password_hash=hash_pwd("testpwd"))
    user2 = UserDB(id=2, email="test2@gmail.com", password_hash=hash_pwd("testpwd"))
    task1 = TaskDB(id=1, title="Sample Task 1", user_id=1)
    task2 = TaskDB(id=2, title="Sample Task 2", completed=True, user_id=1)
    task3 = TaskDB(id=3, title="Sample Task 3", user_id=2)
    db.add(user1)
    db.add(user2)
    db.add(task1)
    db.add(task2)
    db.add(task3)
    db.commit()
    db.close()

    yield

    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def log_user():
    data = LoginInput(email="test1@gmail.com", password="testpwd")
    response = client.post("/login", json=data.model_dump())
    print("DEBUG: Token response:", response.json())  # Depuración del token
    return response.json()["access_token"]


# General tests ----------------------------------------------------------------------------
def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Server is running!"}


def test_non_existent_endpoint():
    response = client.get("/non-existing-endpoint/")
    assert response.status_code == 404


# Get Tasks ----------------------------------------------------------------------------
def test_get_task(setup, log_user):
    header = {"Authorization": f"Bearer {log_user}"}
    response = client.get("/tasks/1", headers=header)
    assert response.status_code == 200
    assert response.json() == OutputTask(id=1, title="Sample Task 1", completed=False, user_id=1).model_dump()


def test_get_non_existing_task(setup, log_user):
    header = {"Authorization": f"Bearer {log_user}"}
    response = client.get("/tasks/99", headers=header)
    assert response.status_code == 404


def test_get_task_invalid_id(setup, log_user):
    header = {"Authorization": f"Bearer {log_user}"}
    response = client.get("/tasks/-1", headers=header)
    assert response.status_code == 422
    assert response.json()["detail"][0]["msg"] == "Input should be greater than 0"


def test_get_task_str_id(setup, log_user):
    header = {"Authorization": f"Bearer {log_user}"}
    response = client.get("/tasks/hello", headers=header)
    assert response.status_code == 422


def test_get_task_float_id(setup, log_user):
    header = {"Authorization": f"Bearer {log_user}"}
    response = client.get("/tasks/1.0", headers=header)
    assert response.status_code == 200
    assert response.json() == OutputTask(id=1, title="Sample Task 1", completed=False, user_id=1).model_dump()


def test_get_task_after_delete(setup, log_user):
    header = {"Authorization": f"Bearer {log_user}"}
    response_get_1 = client.get("/tasks/1", headers=header)
    assert response_get_1.status_code == 200
    assert (
        response_get_1.json()
        == OutputTask(id=1, title="Sample Task 1", completed=False, user_id=1).model_dump()
    )

    response_delete = client.delete("/tasks/1", headers=header)
    assert response_delete.status_code == 202
    assert (
        response_delete.json()
        == OutputTask(id=1, title="Sample Task 1", completed=False, user_id=1).model_dump()
    )

    response_get_2 = client.get("/tasks/1", headers=header)
    assert response_get_2.status_code == 404


# Create Tasks ----------------------------------------------------------------------------
def test_create_task_without_completed(setup, log_user):
    header = {"Authorization": f"Bearer {log_user}"}
    data = InputTask(title="New Task", user_id=1).model_dump()
    response = client.post("/tasks/", json=data, headers=header)
    assert response.status_code == 201
    assert response.json() == OutputTask(id=4, title="New Task", completed=False, user_id=1).model_dump()


def test_create_task_without_title(setup, log_user):
    header = {"Authorization": f"Bearer {log_user}"}
    data = {"user_id": 1}
    response = client.post("/tasks/", json=data, headers=header)
    assert response.status_code == 422
    assert response.json()["detail"][0]["msg"] == "Field required"


def test_create_task_without_user(setup, log_user):
    header = {"Authorization": f"Bearer {log_user}"}
    data = {"title": "I have no user."}
    response = client.post("/tasks/", json=data, headers=header)
    assert response.status_code == 422
    assert response.json()["detail"][0]["msg"] == "Field required"


def test_create_task_with_non_existing_user(setup, log_user):
    header = {"Authorization": f"Bearer {log_user}"}
    data = InputTask(title="New Task", user_id=3).model_dump()
    response = client.post("/tasks/", json=data, headers=header)
    assert response.status_code == 422
    assert response.json()["detail"] == "User with id 3 does not exist"


def test_create_task_with_invalid_user(setup, log_user):
    header = {"Authorization": f"Bearer {log_user}"}
    data = {"title": "New Task", "user_id": -1}
    response = client.post("/tasks/", json=data, headers=header)
    assert response.status_code == 422
    assert response.json()["detail"][0]["msg"] == "Input should be greater than 0"


def test_create_task_with_completed(setup, log_user):
    header = {"Authorization": f"Bearer {log_user}"}
    data = InputTask(title="Another Task", completed=True, user_id=1).model_dump()
    response = client.post("/tasks/", json=data, headers=header)
    assert response.status_code == 201
    assert response.json() == OutputTask(id=4, title="Another Task", completed=True, user_id=1).model_dump()


def test_create_task_with_id(setup, log_user):
    header = {"Authorization": f"Bearer {log_user}"}
    data = {"id": 99, "title": "Task 99", "user_id": 1}
    response = client.post("/tasks/", json=data, headers=header)
    assert response.status_code == 422
    assert response.json()["detail"][0]["msg"] == "Extra inputs are not permitted"


# List tasks
def test_get_tasks(setup, log_user):
    header = {"Authorization": f"Bearer {log_user}"}
    response = client.get("/tasks/", headers=header)
    assert response.status_code == 200
    assert response.json() == [
        OutputTask(id=1, title="Sample Task 1", completed=False, user_id=1).model_dump(),
        OutputTask(id=2, title="Sample Task 2", completed=True, user_id=1).model_dump(),
    ]


def test_get_tasks_after_delete(setup, log_user):
    header = {"Authorization": f"Bearer {log_user}"}
    response_delete = client.delete("/tasks/1", headers=header)
    assert response_delete.status_code == 202
    assert (
        response_delete.json()
        == OutputTask(id=1, title="Sample Task 1", completed=False, user_id=1).model_dump()
    )

    response_list = client.get("/tasks/", headers=header)
    assert response_list.status_code == 200
    assert response_list.json() == [
        OutputTask(id=2, title="Sample Task 2", completed=True, user_id=1).model_dump()
    ]


# Delete task
def test_delete_task(setup, log_user):
    header = {"Authorization": f"Bearer {log_user}"}
    response_delete = client.delete("/tasks/1", headers=header)
    assert response_delete.status_code == 202
    assert (
        response_delete.json()
        == OutputTask(id=1, title="Sample Task 1", completed=False, user_id=1).model_dump()
    )


def test_delete_non_existent_task(setup, log_user):
    header = {"Authorization": f"Bearer {log_user}"}
    response_delete = client.delete("/tasks/99", headers=header)
    assert response_delete.status_code == 404


def test_delete_task_with_negative_id(setup, log_user):
    header = {"Authorization": f"Bearer {log_user}"}
    response_delete = client.delete("/tasks/-1", headers=header)
    assert response_delete.status_code == 422
    assert response_delete.json()["detail"][0]["msg"] == "Input should be greater than 0"


# Update Task
def test_update_task(setup, log_user):
    header = {"Authorization": f"Bearer {log_user}"}
    data = InputTask(title="Updated Task 1", user_id=1).model_dump()
    response_put = client.put("/tasks/1", json=data, headers=header)
    assert response_put.status_code == 202
    assert (
        response_put.json()
        == OutputTask(id=1, title="Updated Task 1", completed=False, user_id=1).model_dump()
    )


def test_update_non_existing_task(setup, log_user):
    header = {"Authorization": f"Bearer {log_user}"}
    data = InputTask(title="Updated Unexisting Task", user_id=1).model_dump()
    response = client.put("/tasks/99", json=data, headers=header)
    assert response.status_code == 404


def test_update_task_with_negative_id(setup, log_user):
    header = {"Authorization": f"Bearer {log_user}"}
    data = InputTask(title="Updated Unexisting Task", user_id=1).model_dump()
    response = client.put("/tasks/-1", json=data, headers=header)
    assert response.status_code == 422
    assert response.json()["detail"][0]["msg"] == "Input should be greater than 0"
    assert response.json()["detail"][0]["msg"] == "Input should be greater than 0"
