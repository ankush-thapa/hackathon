from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import Base, get_db
from app.main import app
from app.models import User

engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSession = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_hello_returns_user_name():
    with TestingSession() as db:
        db.merge(User(id=1, name="Alice"))
        db.commit()
    assert client.get("/hello/1").json() == {"message": "Hello Alice"}


def test_hello_unknown_user_404():
    assert client.get("/hello/999").status_code == 404


def test_list_users_returns_ids():
    with TestingSession() as db:
        db.merge(User(id=1, name="Alice"))
        db.merge(User(id=2, name="Bob"))
        db.commit()
    assert client.get("/users").json() == [{"id": 1}, {"id": 2}]
