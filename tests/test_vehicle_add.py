import pytest
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


@pytest.mark.parametrize(
    "patch",
    [
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


def test_photo_creation_can_be_read_and_updated_through_crud(client, auth):
    headers = auth[1]
    created = client.post(URL, json=payload(), headers=headers)
    assert created.status_code == 201
    vehicle_id = created.json()["id"]
    fetched = client.get(f"{URL}/{vehicle_id}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["photoUrl"] == PHOTO
    assert fetched.json()["vehicleType"] == "car"
    updated = client.patch(f"{URL}/{vehicle_id}", json={"photoUrl": None, "color": "Blue"}, headers=headers)
    assert updated.status_code == 200
    assert updated.json()["photoUrl"] is None
    assert updated.json()["color"] == "Blue"


def test_registration_unique_across_request_formats(client, auth):
    headers = auth[1]
    assert client.post(URL, json=payload(), headers=headers).status_code == 201
    response = client.post(URL, json={
        "make": "Maruti", "model": "Swift", "color": "White",
        "registrationNumber": "MH-12-AB-1234", "seatCapacity": 4, "vehicleType": "hatchback",
    }, headers=headers)
    assert response.status_code == 409


def test_first_active_vehicle_becomes_default_after_deactivation(client, auth):
    headers = auth[1]
    created = client.post(URL, json=payload(), headers=headers).json()
    response = client.patch(f"{URL}/{created['id']}", json={"status": "inactive"}, headers=headers)
    assert response.status_code == 200
    second = client.post(URL, json=payload(registration_number="22BH1234AA"), headers=headers)
    assert second.status_code == 201
    assert second.json()["is_default"] is True
