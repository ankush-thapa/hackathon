from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import Base, get_db
from app.main import app
from app.models import User, UserProfile

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


def _add_user(db, uid, user_name, full_name=None):
    db.merge(User(id_user=uid, user_name=user_name, password_hash="x"))
    db.flush()
    if full_name:
        db.merge(UserProfile(id_user=uid, full_name=full_name))


def test_hello_returns_profile_name():
    with TestingSession() as db:
        _add_user(db, 1, "alice", "Alice")
        db.commit()
    assert client.get("/hello/1").json() == {"message": "Hello Alice"}


def test_hello_falls_back_to_user_name_without_profile():
    with TestingSession() as db:
        _add_user(db, 3, "carol")
        db.commit()
    assert client.get("/hello/3").json() == {"message": "Hello carol"}


def test_hello_unknown_user_404():
    assert client.get("/hello/999").status_code == 404


def _auth_headers():
    creds = {"email": "lister@example.com", "phone": "+971505550000", "password": "Secret123"}
    client.post("/v1/auth/register", json=creds)  # 409 on reruns within the module is fine
    token = client.post("/v1/auth/login", json={"email": creds["email"], "password": creds["password"]}).json()
    return {"Authorization": f"Bearer {token['accessToken']}"}


def test_list_users_returns_string_ids():
    with TestingSession() as db:
        _add_user(db, 1, "alice", "Alice")
        _add_user(db, 2, "bob", "Bob")
        db.commit()
    ids = [u["id"] for u in client.get("/users", headers=_auth_headers()).json()]
    assert {"1", "2"} <= set(ids)


def test_list_users_requires_session():
    r = client.get("/users")
    assert r.status_code == 401
    assert r.json()["detail"]["code"] == "token_missing"
