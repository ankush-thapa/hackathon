import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import Base, get_db
from app.main import app

REG = "/v1/auth/register"
URL = "/v1/auth/profile"


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


@pytest.fixture
def user_id(client):
    r = client.post(REG, json={"email": "jane@example.com", "phone": "+971503333333", "password": "Secret123"})
    return int(r.json()["userId"])


def payload(uid, **kw):
    return {"userId": uid, "fullName": "  Jane Doe ", "about": "Commuter", "dateOfBirth": "1995-04-12",
            "gender": "female", **kw}


def test_create_profile(client, user_id):
    r = client.post(URL, json=payload(user_id))
    assert r.status_code == 201
    assert r.json() == {"userId": str(user_id), "fullName": "Jane Doe", "photoUrl": None, "about": "Commuter",
                        "dateOfBirth": "1995-04-12", "gender": "female"}
    with client.session() as db:
        row = db.execute(text("SELECT full_name, gender FROM user_profile WHERE id_user = :i"), {"i": user_id}).one()
        assert (row.full_name, row.gender) == ("Jane Doe", "female")


def test_minimal_profile(client, user_id):
    assert client.post(URL, json={"userId": user_id, "fullName": "Jane"}).status_code == 201


def test_unknown_user_404(client):
    assert client.post(URL, json={"userId": 123, "fullName": "Jane"}).status_code == 404


def test_second_post_updates_and_replaces(client, user_id):
    assert client.post(URL, json=payload(user_id)).status_code == 201
    r = client.post(URL, json={"userId": user_id, "fullName": "Jane Smith", "photoUrl": "k/p.jpg"})
    assert r.status_code == 200
    assert r.json() == {"userId": str(user_id), "fullName": "Jane Smith", "photoUrl": "k/p.jpg", "about": None,
                        "dateOfBirth": None, "gender": None}
    with client.session() as db:
        rows = db.execute(text("SELECT full_name, about, gender FROM user_profile")).all()
        assert [tuple(r) for r in rows] == [("Jane Smith", None, None)]  # one row, omitted fields cleared


@pytest.mark.parametrize(
    "patch",
    [
        {"fullName": ""},
        {"fullName": "   "},
        {"fullName": "x" * 101},
        {"about": "x" * 501},
        {"gender": "robot"},
        {"dateOfBirth": "2999-01-01"},
        {"dateOfBirth": "not-a-date"},
        {"userId": 0},
    ],
)
def test_validation_422(client, user_id, patch):
    assert client.post(URL, json=payload(user_id, **patch)).status_code == 422


def _login_flag(client):
    r = client.post("/v1/auth/login", json={"email": "jane@example.com", "password": "Secret123"})
    assert r.status_code == 200
    return r.json()["isProfileCompleted"]


def test_saving_profile_marks_user_profile_completed(client, user_id):
    assert _login_flag(client) is False
    assert client.post(URL, json=payload(user_id)).status_code == 201
    assert _login_flag(client) is True
    # Replacing the profile keeps the flag set.
    assert client.post(URL, json=payload(user_id, about="Updated")).status_code == 200
    assert _login_flag(client) is True
    with client.session() as db:
        flag = db.execute(text("SELECT is_profile_completed FROM `user` WHERE id_user = :i"), {"i": user_id})
        assert flag.scalar() == 1
