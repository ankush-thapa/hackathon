import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import verify_password
from app.db.session import Base, get_db
from app.main import app

URL = "/v1/auth/register"
VALID = {"email": "Jane@Example.com", "phone": "+971503333333", "password": "Secret123"}


@pytest.fixture
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    def override():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override
    c = TestClient(app)
    c.session = Session
    yield c
    if previous is None:
        app.dependency_overrides.pop(get_db, None)
    else:
        app.dependency_overrides[get_db] = previous


def test_register_persists_user(client):
    r = client.post(URL, json=VALID)
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "jane@example.com"
    assert body["phone"] == VALID["phone"]
    assert isinstance(body["userId"], str)
    assert "password" not in body and "password_hash" not in body
    with client.session() as db:
        row = db.execute(
            text("SELECT user_name, status, password_hash FROM `user` WHERE id_user = :i"), {"i": int(body["userId"])}
        ).one()
        assert row.user_name is None
        assert row.status == "active"
        assert row.password_hash != VALID["password"]
        assert verify_password(VALID["password"], row.password_hash)


@pytest.mark.parametrize(
    "patch, field",
    [
        ({}, "email"),
        ({"email": "JANE@example.com", "phone": "+971500000001"}, "email"),
        ({"email": "x@example.com"}, "phone"),
    ],
)
def test_duplicates_409(client, patch, field):
    assert client.post(URL, json=VALID).status_code == 201
    r = client.post(URL, json={**VALID, **patch})
    assert r.status_code == 409
    assert r.json()["detail"] == f"{field} already registered"


@pytest.mark.parametrize(
    "patch",
    [
        {"email": "not-an-email"},
        {"phone": "0501234567"},
        {"phone": "+12"},
        {"password": "short1"},
        {"password": "onlyletters"},
        {"password": "12345678"},
    ],
)
def test_validation_errors_422(client, patch):
    assert client.post(URL, json={**VALID, **patch}).status_code == 422


def test_missing_fields_422(client):
    assert client.post(URL, json={"email": "a@b.co"}).status_code == 422
