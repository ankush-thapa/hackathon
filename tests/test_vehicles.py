import pytest
<<<<<<< Updated upstream
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import Base, get_db
from app.main import app

URL = "/v1/vehicles"
PHOTO = "http://localhost:8000/media/abc123.jpg"


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


def login(client, email="jane@example.com", phone="+971503333333"):
    user = {"email": email, "phone": phone, "password": "Secret123"}
    user_id = int(client.post("/v1/auth/register", json=user).json()["userId"])
    token = client.post("/v1/auth/login", json={"email": email, "password": "Secret123"}).json()["accessToken"]
    return user_id, {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth(client):
    return login(client)


def payload(**kw):
    return {"photo_url": PHOTO, "make": " Maruti  Suzuki ", "model": "Swift", "registration_number": "mh 12-ab 1234",
            "colour": "Pearl White", "seat_capacity": 4, **kw}


def test_add_vehicle(client, auth):
    user_id, headers = auth
    r = client.post(URL, json=payload(), headers=headers)
    assert r.status_code == 201
    body = r.json()
    assert body.pop("id").isdigit()
    assert body == {"photo_url": PHOTO, "make": "Maruti Suzuki", "model": "Swift", "registration_number": "MH12AB1234",
                    "colour": "Pearl White", "seat_capacity": 4, "vehicle_type": "car", "is_default": True,
                    "status": "active"}
    with client.session() as db:
        row = db.execute(text("SELECT id_user, color, vehicle_type, car_photo, is_default FROM vehicle")).one()
        assert (row.id_user, row.color, row.vehicle_type, row.car_photo, bool(row.is_default)) == (
            user_id, "Pearl White", "car", PHOTO, True)


def test_only_first_vehicle_is_default(client, auth):
    _, headers = auth
    assert client.post(URL, json=payload(), headers=headers).json()["is_default"] is True
    second = client.post(URL, json=payload(registration_number="22 BH 1234 AA", vehicle_type="suv"), headers=headers)
    assert second.status_code == 201
    assert second.json()["is_default"] is False and second.json()["vehicle_type"] == "suv"


def test_duplicate_registration_409_even_across_users(client, auth):
    _, headers = auth
    assert client.post(URL, json=payload(), headers=headers).status_code == 201
    _, other = login(client, "sam@example.com", "+971504444444")
    r = client.post(URL, json=payload(registration_number="MH12AB1234"), headers=other)
    assert r.status_code == 409
    assert r.json()["detail"] == "registration_number already registered"


def test_requires_login(client):
    assert client.post(URL, json=payload()).status_code == 401
    assert client.post(URL, json=payload(), headers={"Authorization": "Bearer nope"}).status_code == 401


@pytest.mark.parametrize("reg", ["MH12AB1234", "DL 3C AB 1234", "KA-05-1234", "22BH1234A"])
def test_valid_registrations(client, auth, reg):
    assert client.post(URL, json=payload(registration_number=reg), headers=auth[1]).status_code == 201
=======
from sqlalchemy import text

from tests.test_auth_login import USER, auth, client, login  # noqa: F401  (client is a fixture)

URL = "/v1/vehicles"
CAR = {
    "make": " Toyota ", "model": "Corolla", "color": "White",
    "registrationNumber": "ka 01 ab 1234", "seatCapacity": 4, "vehicleType": "sedan",
}


@pytest.fixture
def h(client):
    return auth(login(client))


def other_user_headers(client):
    other = {"email": "other@example.com", "phone": "+971504444444", "password": "Secret123"}
    client.post("/v1/auth/register", json=other)
    return auth(client.post("/v1/auth/login", json={"email": other["email"], "password": other["password"]}).json())


def add(client, h, **kw):
    r = client.post(URL, json={**CAR, **kw}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def test_create_normalizes_and_first_is_default(client, h):
    v = add(client, h)
    assert v["make"] == "Toyota" and v["registrationNumber"] == "KA01AB1234"
    assert v["isDefault"] is True and v["status"] == "active"
    assert v["createdAt"].endswith("Z") and isinstance(v["vehicleId"], str)
    with client.session() as db:
        owner = db.execute(text("SELECT id_user FROM vehicle WHERE id_vehicle = :i"), {"i": int(v["vehicleId"])}).scalar()
    assert owner == client.user_id


def test_second_vehicle_not_default_unless_asked(client, h):
    first = add(client, h)
    second = add(client, h, registrationNumber="B2")
    assert second["isDefault"] is False
    third = add(client, h, registrationNumber="C3", isDefault=True)
    assert third["isDefault"] is True
    by_id = {v["vehicleId"]: v for v in client.get(URL, headers=h).json()}
    assert [by_id[x["vehicleId"]]["isDefault"] for x in (first, second, third)] == [False, False, True]


def test_list_default_first_and_status_filter(client, h):
    a = add(client, h)
    b = add(client, h, registrationNumber="B2")
    client.patch(f"{URL}/{b['vehicleId']}", json={"status": "inactive"}, headers=h)
    assert [v["vehicleId"] for v in client.get(URL, headers=h).json()] == [a["vehicleId"], b["vehicleId"]]
    assert [v["vehicleId"] for v in client.get(URL, params={"status": "inactive"}, headers=h).json()] == [b["vehicleId"]]
    assert client.get(URL, params={"status": "deleted"}, headers=h).status_code == 422


def test_get_one(client, h):
    v = add(client, h)
    assert client.get(f"{URL}/{v['vehicleId']}", headers=h).json() == v
    assert client.get(f"{URL}/123", headers=h).status_code == 404


def test_patch_partial_update(client, h):
    v = add(client, h)
    r = client.patch(f"{URL}/{v['vehicleId']}", json={"color": " Red ", "seatCapacity": 5}, headers=h)
    assert r.status_code == 200
    body = r.json()
    assert (body["color"], body["seatCapacity"], body["make"]) == ("Red", 5, "Toyota")


def test_patch_default_moves(client, h):
    a = add(client, h)
    b = add(client, h, registrationNumber="B2")
    assert client.patch(f"{URL}/{b['vehicleId']}", json={"isDefault": True}, headers=h).json()["isDefault"] is True
    assert client.get(f"{URL}/{a['vehicleId']}", headers=h).json()["isDefault"] is False


def test_deactivating_default_clears_it_and_inactive_cannot_be_default(client, h):
    v = add(client, h)
    r = client.patch(f"{URL}/{v['vehicleId']}", json={"status": "inactive"}, headers=h)
    assert (r.json()["status"], r.json()["isDefault"]) == ("inactive", False)
    r = client.patch(f"{URL}/{v['vehicleId']}", json={"isDefault": True}, headers=h)
    assert r.status_code == 409
    assert client.patch(f"{URL}/{v['vehicleId']}", json={"status": "active", "isDefault": True}, headers=h).status_code == 200


def test_duplicate_registration_409(client, h):
    add(client, h)
    assert client.post(URL, json={**CAR, "registrationNumber": "KA01 AB1234"}, headers=h).status_code == 409
    b = add(client, h, registrationNumber="B2")
    r = client.patch(f"{URL}/{b['vehicleId']}", json={"registrationNumber": "ka01ab1234"}, headers=h)
    assert r.status_code == 409
    # another user can't take it either
    assert client.post(URL, json=CAR, headers=other_user_headers(client)).status_code == 409


def test_delete_is_soft_and_frees_registration(client, h):
    v = add(client, h)
    assert client.delete(f"{URL}/{v['vehicleId']}", headers=h).status_code == 204
    assert client.get(f"{URL}/{v['vehicleId']}", headers=h).status_code == 404
    assert client.get(URL, headers=h).json() == []
    assert client.delete(f"{URL}/{v['vehicleId']}", headers=h).status_code == 404
    assert client.patch(f"{URL}/{v['vehicleId']}", json={"color": "Red"}, headers=h).status_code == 404
    again = add(client, h)  # same registration number, now free
    assert again["vehicleId"] != v["vehicleId"] and again["isDefault"] is True


def test_cannot_touch_other_users_vehicle(client, h):
    v = add(client, h)
    theirs = other_user_headers(client)
    for method in ("get", "patch", "delete"):
        kwargs = {"json": {"color": "Red"}} if method == "patch" else {}
        r = getattr(client, method)(f"{URL}/{v['vehicleId']}", headers=theirs, **kwargs)
        assert r.status_code == 404, method
    assert client.get(URL, headers=theirs).json() == []
    assert client.get(f"{URL}/{v['vehicleId']}", headers=h).json()["color"] == "White"
>>>>>>> Stashed changes


@pytest.mark.parametrize(
    "patch",
    [
<<<<<<< Updated upstream
        {"photo_url": ""},
        {"photo_url": "file:///tmp/a.jpg"},
        {"make": "   "},
        {"model": ""},
        {"colour": "x" * 31},
        {"make": "x" * 51},
        {"registration_number": "ABC 1234"},
        {"registration_number": "MH 12 ABCDE 1234"},
        {"registration_number": "DL 01 AB 12345"},
        {"seat_capacity": 0},
        {"seat_capacity": 9},
        {"vehicle_type": "truck"},
    ],
)
def test_validation_422(client, auth, patch):
    assert client.post(URL, json=payload(**patch), headers=auth[1]).status_code == 422


def test_missing_fields_422(client, auth):
    body = payload()
    del body["seat_capacity"]
    assert client.post(URL, json=body, headers=auth[1]).status_code == 422
=======
        {"seatCapacity": 0}, {"seatCapacity": 9}, {"vehicleType": "truck"}, {"make": "  "},
        {"registrationNumber": "AB#12"}, {"make": "x" * 51},
    ],
)
def test_create_validation_422(client, h, patch):
    assert client.post(URL, json={**CAR, **patch}, headers=h).status_code == 422


@pytest.mark.parametrize("body", [{}, {"color": None}, {"status": "deleted"}, {"seatCapacity": 12}])
def test_patch_validation_422(client, h, body):
    v = add(client, h)
    assert client.patch(f"{URL}/{v['vehicleId']}", json=body, headers=h).status_code == 422


@pytest.mark.parametrize(
    "method, path", [("post", URL), ("get", URL), ("get", f"{URL}/1"), ("patch", f"{URL}/1"), ("delete", f"{URL}/1")]
)
def test_all_routes_need_session(client, method, path):
    kwargs = {"json": CAR} if method in ("post", "patch") else {}
    r = getattr(client, method)(path, **kwargs)
    assert r.status_code == 401 and r.json()["detail"]["code"] == "token_missing"
>>>>>>> Stashed changes
