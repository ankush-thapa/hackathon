import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import decode_access_token
from app.db.session import Base, get_db
from app.main import app

URL = "/v1/auth/login"
USER = {"email": "jane@example.com", "phone": "+971503333333", "password": "Secret123"}


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
    c.user_id = int(c.post("/v1/auth/register", json=USER).json()["userId"])
    yield c
    if previous is None:
        app.dependency_overrides.pop(get_db, None)
    else:
        app.dependency_overrides[get_db] = previous


def set_status(client, status):
    with client.session() as db:
        db.execute(text("UPDATE `user` SET status = :s WHERE id_user = :i"), {"s": status, "i": client.user_id})
        db.commit()


@pytest.mark.parametrize(
    "identifier", [{"email": USER["email"]}, {"email": "  JANE@Example.com "}, {"phone": USER["phone"]}]
)
def test_login_returns_token(client, identifier):
    r = client.post(URL, json={**identifier, "password": USER["password"]})
    assert r.status_code == 200
    assert r.headers["cache-control"] == "no-store"
    body = r.json()
    assert body["userId"] == str(client.user_id)
    assert body["tokenType"] == "Bearer" and body["expiresIn"] > 0
    assert decode_access_token(body["accessToken"])["sub"] == str(client.user_id)
    with client.session() as db:
        last_active = db.execute(text("SELECT last_active FROM `user` WHERE id_user = :i"), {"i": client.user_id})
        assert last_active.scalar() is not None


@pytest.mark.parametrize(
    "payload",
    [
        {"email": USER["email"], "password": "Wrong1234"},
        {"phone": USER["phone"], "password": "Wrong1234"},
        {"email": "nobody@example.com", "password": USER["password"]},
        {"phone": "+971500000009", "password": USER["password"]},
    ],
)
def test_bad_credentials_401_same_message(client, payload):
    r = client.post(URL, json=payload)
    assert r.status_code == 401
    assert r.json() == {"detail": "invalid credentials"}


def test_deleted_account_looks_unknown(client):
    set_status(client, "deleted")
    r = client.post(URL, json={"email": USER["email"], "password": USER["password"]})
    assert r.status_code == 401
    assert r.json() == {"detail": "invalid credentials"}


def test_blocked_account_403_only_with_right_password(client):
    set_status(client, "blocked")
    assert client.post(URL, json={"email": USER["email"], "password": USER["password"]}).status_code == 403
    assert client.post(URL, json={"email": USER["email"], "password": "Wrong1234"}).status_code == 401


@pytest.mark.parametrize(
    "payload",
    [
        {"password": "Secret123"},
        {"email": USER["email"], "phone": USER["phone"], "password": "Secret123"},
        {"email": "not-an-email", "password": "Secret123"},
        {"phone": "0501234567", "password": "Secret123"},
        {"email": USER["email"], "password": ""},
        {"email": USER["email"]},
    ],
)
def test_validation_errors_422(client, payload):
    assert client.post(URL, json=payload).status_code == 422
