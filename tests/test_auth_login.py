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


def login(client, **headers):
    r = client.post(URL, json={"email": USER["email"], "password": USER["password"]}, headers=headers)
    assert r.status_code == 200
    return r.json()


def auth(body):
    return {"Authorization": f"Bearer {body['accessToken']}"}


def test_login_creates_session_bound_to_token(client):
    body = login(client, **{"User-Agent": "phone-app/1.0"})
    assert decode_access_token(body["accessToken"])["sid"] == body["sessionId"]
    with client.session() as db:
        row = db.execute(
            text("SELECT id_user, user_agent, revoked_at, expires_at > created_at AS live FROM user_session "
                 "WHERE id_session = :s"), {"s": int(body["sessionId"])}
        ).one()
    assert (row.id_user, row.user_agent, row.revoked_at, bool(row.live)) == (client.user_id, "phone-app/1.0", None, True)


def test_list_sessions_marks_current(client):
    first, second = login(client), login(client)
    r = client.get("/v1/auth/sessions", headers=auth(second))
    assert r.status_code == 200
    sessions = r.json()
    assert [s["sessionId"] for s in sessions] == [second["sessionId"], first["sessionId"]]
    assert [s["current"] for s in sessions] == [True, False]


def test_logout_revokes_only_that_session(client):
    first, second = login(client), login(client)
    assert client.post("/v1/auth/logout", headers=auth(first)).status_code == 204
    assert client.get("/v1/auth/sessions", headers=auth(first)).status_code == 401
    assert client.post("/v1/auth/logout", headers=auth(first)).status_code == 401
    remaining = client.get("/v1/auth/sessions", headers=auth(second)).json()
    assert [s["sessionId"] for s in remaining] == [second["sessionId"]]


def test_revoke_other_session(client):
    lost, mine = login(client), login(client)
    assert client.delete(f"/v1/auth/sessions/{lost['sessionId']}", headers=auth(mine)).status_code == 204
    assert client.get("/v1/auth/sessions", headers=auth(lost)).status_code == 401
    assert client.delete(f"/v1/auth/sessions/{lost['sessionId']}", headers=auth(mine)).status_code == 404


def test_cannot_revoke_someone_elses_session(client):
    other = {"email": "other@example.com", "phone": "+971504444444", "password": "Secret123"}
    assert client.post("/v1/auth/register", json=other).status_code == 201
    theirs = client.post(URL, json={"email": other["email"], "password": other["password"]}).json()
    mine = login(client)
    assert client.delete(f"/v1/auth/sessions/{theirs['sessionId']}", headers=auth(mine)).status_code == 404
    assert client.get("/v1/auth/sessions", headers=auth(theirs)).status_code == 200


def test_blocking_user_ends_their_sessions(client):
    body = login(client)
    set_status(client, "blocked")
    assert client.get("/v1/auth/sessions", headers=auth(body)).status_code == 401


def test_expired_session_rejected(client):
    body = login(client)
    with client.session() as db:
        db.execute(text("UPDATE user_session SET expires_at = '2000-01-01' WHERE id_session = :s"),
                   {"s": int(body["sessionId"])})
        db.commit()
    assert client.get("/v1/auth/sessions", headers=auth(body)).status_code == 401


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Bearer not-a-jwt"},
        {"Authorization": "Basic abc"},
    ],
)
def test_protected_routes_need_valid_bearer(client, headers):
    r = client.get("/v1/auth/sessions", headers=headers)
    assert r.status_code == 401
    assert r.headers["www-authenticate"] == "Bearer"


def test_token_without_sid_rejected(client):
    import jwt
    from app.core.config import settings

    legacy = jwt.encode({"sub": str(client.user_id), "exp": 4102444800}, settings.JWT_SECRET, algorithm="HS256")
    assert client.get("/v1/auth/sessions", headers={"Authorization": f"Bearer {legacy}"}).status_code == 401


def test_session_times_are_utc_marked(client):
    body = login(client)
    s = client.get("/v1/auth/sessions", headers=auth(body)).json()[0]
    assert s["createdAt"].endswith("Z") and s["expiresAt"].endswith("Z")
