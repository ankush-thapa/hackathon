from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.api.deps import SESSION_ERROR_MESSAGES, require_session
from app.core.config import settings
from app.db.session import get_db
from app.services.auth_service import SessionReason
from tests.test_auth_login import USER, auth, client, login, set_status  # noqa: F401  (client is a fixture)

REFRESH = "/v1/auth/refresh"


def code(r):
    return r.json()["detail"]["code"]


def set_session_expiry(client, session_id, when):
    with client.session() as db:
        db.execute(text("UPDATE user_session SET expires_at = :w WHERE id_session = :s"), {"w": when, "s": int(session_id)})
        db.commit()


def expired_access_token(client, body):
    past = datetime.now(timezone.utc) - timedelta(minutes=1)
    claims = {"sub": str(client.user_id), "sid": body["sessionId"], "iat": past - timedelta(hours=1), "exp": past}
    return jwt.encode(claims, settings.JWT_SECRET, algorithm="HS256")


# --- refresh ---------------------------------------------------------------------------------

def test_login_returns_refresh_token_and_session_lifetime(client):
    body = login(client)
    assert body["refreshToken"].startswith(body["sessionId"] + ".")
    lifetime = datetime.fromisoformat(body["sessionExpiresAt"]) - datetime.now(timezone.utc)
    assert timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS - 1) < lifetime <= timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    with client.session() as db:
        stored = db.execute(text("SELECT refresh_token_hash FROM user_session WHERE id_session = :s"),
                            {"s": int(body["sessionId"])}).scalar()
    assert len(stored) == 64 and body["refreshToken"].split(".")[1] not in stored


def test_refresh_rotates_tokens_in_same_session(client):
    body = login(client)
    r = client.post(REFRESH, json={"refreshToken": body["refreshToken"]})
    assert r.status_code == 200
    assert r.headers["cache-control"] == "no-store"
    new = r.json()
    assert new["sessionId"] == body["sessionId"] and new["userId"] == body["userId"]
    assert new["refreshToken"] != body["refreshToken"]
    assert new["sessionExpiresAt"] == body["sessionExpiresAt"]  # refreshing never extends the session
    assert client.get("/v1/auth/sessions", headers=auth(new)).status_code == 200
    # and the new refresh token is usable in turn
    assert client.post(REFRESH, json={"refreshToken": new["refreshToken"]}).status_code == 200


def test_reused_refresh_token_revokes_session(client):
    body = login(client)
    new = client.post(REFRESH, json={"refreshToken": body["refreshToken"]}).json()
    r = client.post(REFRESH, json={"refreshToken": body["refreshToken"]})
    assert r.status_code == 401 and code(r) == "session_revoked"
    # the legitimate holder of the newer tokens is logged out too
    assert code(client.get("/v1/auth/sessions", headers=auth(new))) == "session_revoked"
    assert code(client.post(REFRESH, json={"refreshToken": new["refreshToken"]})) == "session_revoked"


def test_refresh_works_after_access_token_expired(client):
    body = login(client)
    stale = {"accessToken": expired_access_token(client, body)}
    assert code(client.get("/v1/auth/sessions", headers=auth(stale))) == "token_expired"
    new = client.post(REFRESH, json={"refreshToken": body["refreshToken"]}).json()
    assert client.get("/v1/auth/sessions", headers=auth(new)).status_code == 200


@pytest.mark.parametrize("token", ["garbage", "123", "abc.def", "999999.secret", ""])
def test_refresh_rejects_malformed_or_unknown(client, token):
    r = client.post(REFRESH, json={"refreshToken": token})
    assert r.status_code in (401, 422)
    if r.status_code == 401:
        assert code(r) == "token_invalid"


def test_refresh_after_logout(client):
    body = login(client)
    client.post("/v1/auth/logout", headers=auth(body))
    assert code(client.post(REFRESH, json={"refreshToken": body["refreshToken"]})) == "session_revoked"


def test_refresh_after_session_expired(client):
    body = login(client)
    set_session_expiry(client, body["sessionId"], "2000-01-01")
    assert code(client.post(REFRESH, json={"refreshToken": body["refreshToken"]})) == "session_expired"


def test_refresh_for_blocked_user(client):
    body = login(client)
    set_status(client, "blocked")
    assert code(client.post(REFRESH, json={"refreshToken": body["refreshToken"]})) == "account_inactive"


def test_access_token_never_outlives_session(client):
    body = login(client)
    soon = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(seconds=30)
    set_session_expiry(client, body["sessionId"], soon)
    new = client.post(REFRESH, json={"refreshToken": body["refreshToken"]}).json()
    assert 0 < new["expiresIn"] <= 30


# --- require_session decorator ---------------------------------------------------------------

@pytest.fixture
def protected(client):
    router = APIRouter()

    @router.get("/me")
    @require_session
    def me(current_user_id: int):
        return {"userId": current_user_id}

    @router.get("/async-me")
    @require_session
    async def async_me(current_user_id: int):
        return {"userId": current_user_id}

    @router.get("/items/{item_id}")
    @require_session
    def item(item_id: int, q: str = "x", *, current_user_id: int):
        return {"item": item_id, "q": q, "userId": current_user_id}

    @router.get("/ping")
    @require_session
    def ping():
        return {"ok": True}

    test_app = FastAPI()
    test_app.include_router(router)
    test_app.dependency_overrides[get_db] = client.app.dependency_overrides[get_db]
    return TestClient(test_app)


@pytest.mark.parametrize("path", ["/me", "/async-me"])
def test_decorator_passes_user_id(client, protected, path):
    r = protected.get(path, headers=auth(login(client)))
    assert r.status_code == 200 and r.json() == {"userId": client.user_id}


def test_decorator_keeps_other_params(client, protected):
    r = protected.get("/items/7?q=hello", headers=auth(login(client)))
    assert r.json() == {"item": 7, "q": "hello", "userId": client.user_id}


def test_decorator_protects_endpoint_without_user_id_param(client, protected):
    assert protected.get("/ping").status_code == 401
    assert protected.get("/ping", headers=auth(login(client))).json() == {"ok": True}


@pytest.mark.parametrize(
    "make_headers, reason",
    [
        (lambda c, b: {}, "token_missing"),
        (lambda c, b: auth({"accessToken": expired_access_token(c, b)}), "token_expired"),
        (lambda c, b: (set_session_expiry(c, b["sessionId"], "2000-01-01"), auth(b))[1], "session_expired"),
        (lambda c, b: (c.post("/v1/auth/logout", headers=auth(b)), auth(b))[1], "session_revoked"),
    ],
)
def test_decorator_rejects_dead_sessions(client, protected, make_headers, reason):
    r = protected.get("/me", headers=make_headers(client, login(client)))
    assert r.status_code == 401
    assert r.json()["detail"] == {"code": reason, "message": SESSION_ERROR_MESSAGES[SessionReason(reason)]}
    assert r.headers["www-authenticate"] == "Bearer"


def test_decorator_hides_user_id_from_openapi(protected):
    params = protected.app.openapi()["paths"]["/me"]["get"].get("parameters", [])
    assert all(p["name"] != "current_user_id" for p in params)


# --- GET /v1/auth/me (example protected API) -------------------------------------------------

def test_me_returns_user_id(client):
    r = client.get("/v1/auth/me", headers=auth(login(client)))
    assert r.status_code == 200 and r.json() == {"userId": str(client.user_id)}


def test_me_with_expired_token(client):
    r = client.get("/v1/auth/me", headers=auth({"accessToken": expired_access_token(client, login(client))}))
    assert r.status_code == 401
    assert r.json() == {"detail": {"code": "token_expired", "message": "user session expired, refresh the token"}}


def test_me_without_token(client):
    r = client.get("/v1/auth/me")
    assert r.status_code == 401 and r.json()["detail"]["code"] == "token_missing"
