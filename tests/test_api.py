import pytest
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import sessionmaker

from src.app import InputTask, OutputTask, app, get_db
from src.model import Base, Task

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


# This will run until the yield for the tests that have it as parameters
@pytest.fixture
def setup_db():
    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    task1 = Task(id=1, title="Sample Task 1")
    task2 = Task(id=2, title="Sample Task 2", completed=False)
    db.add(task1)
    db.add(task2)
    db.commit()
    db.close()

    yield

    Base.metadata.drop_all(bind=engine)


# General tests ----------------------------------------------------------------------------
def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Server is running!"}


def test_non_existent_endpoint():
    response = client.get("/non-existing-endpoint/")
    assert response.status_code == 404


# Get Tasks ----------------------------------------------------------------------------
def test_get_task(setup_db):
    response = client.get("/tasks/1")
    assert response.status_code == 200
    assert response.json() == OutputTask(id=1, title="Sample Task 1", completed=False).model_dump()


def test_get_non_existing_task(setup_db):
    response = client.get("/tasks/99")
    assert response.status_code == 204


def test_get_task_invalid_id(setup_db):
    response = client.get("/tasks/-1")
    assert response.status_code == 422
    assert response.json()["detail"][0]["msg"] == "Input should be greater than 0"


def test_get_task_str_id(setup_db):
    response = client.get("/tasks/hello")
    assert response.status_code == 422


def test_get_task_float_id(setup_db):
    response = client.get("/tasks/1.0")
    assert response.status_code == 200
    assert response.json() == OutputTask(id=1, title="Sample Task 1", completed=False).model_dump()


# Create Tasks ----------------------------------------------------------------------------
def test_create_task_without_completed(setup_db):
    data = InputTask(title="New Task").model_dump()
    response = client.post("/tasks/", json=data)
    assert response.status_code == 201
    assert response.json() == OutputTask(id=3, title="New Task", completed=False).model_dump()


def test_create_task_with_completed(setup_db):
    data = InputTask(title="Another Task", completed=True).model_dump()
    response = client.post("/tasks/", json=data)
    assert response.status_code == 201
    assert response.json() == OutputTask(id=3, title="Another Task", completed=True).model_dump()


def test_create_task_with_id():
    data = {"id": 99, "title": "Task 99"}
    response = client.post("/tasks/", json=data)
    assert response.status_code == 422
    assert response.json()["detail"][0]["msg"] == "Extra inputs are not permitted"


def test_get_tasks(setup_db):
    response = client.get("/tasks/")
    assert response.status_code == 200
    assert response.json() == [
        OutputTask(id=1, title="Sample Task 1", completed=False).model_dump(),
        OutputTask(id=2, title="Sample Task 2", completed=False).model_dump(),
    ]
