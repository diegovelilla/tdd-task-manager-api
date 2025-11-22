import pytest
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import sessionmaker

from src.app import app, get_db
from src.model import Base, Task

client = TestClient(app)

TESTING_SQLITE_URL = "sqlite:///:memory:"
engine = create_engine(TESTING_SQLITE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


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


def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Server is running!"}


def test_non_existent_endpoint():
    response = client.get("/non-existing-endpoint/")
    assert response.status_code == 404


def test_get_task(setup_db):
    response = client.get("/tasks/1")
    assert response.status_code == 200
    assert response.json() == {"id": 1, "title": "Sample Task 1", "completed": False}


def test_get_non_existing_task(setup_db):
    response = client.get("/tasks/-1")
    assert response.status_code == 404


def test_create_task_without_completed(setup_db):
    data = {"title": "New Task"}
    response = client.post("/tasks/", json=data)
    assert response.status_code == 201
    assert response.json() == {"id": 3, "title": "New Task", "completed": False}


def test_create_task_with_completed(setup_db):
    data = {"title": "Another Task", "completed": True}
    response = client.post("/tasks/", json=data)
    assert response.status_code == 201
    assert response.json() == {"id": 3, "title": "Another Task", "completed": True}


def test_get_tasks(setup_db):
    response = client.get("/tasks/")
    assert response.status_code == 200
    assert response.json() == [
        {"id": 1, "title": "Sample Task 1", "completed": False},
        {"id": 2, "title": "Sample Task 2", "completed": False},
    ]
