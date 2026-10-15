from datetime import datetime, timedelta, timezone
from decimal import Decimal

import jwt
import pytest
from sqlalchemy import text

from app.core.config import settings
from app.main import app
from app.models import Station, User, Vehicle
from tests.test_auth_login import auth, client, login  # noqa: F401 (client is a fixture)
from tests.test_migrations_mysql import mysql_database  # noqa: F401 (opt-in fixture)

URL = "/v1/rides/offer"
VEHICLE_ID = 2**53 + 123


@pytest.fixture
def ride_data(client):
    with client.session() as db:
        db.add_all([
            Station(id_station=1, station_name="Source"),
            Station(id_station=2, station_name="Destination"),
            Station(id_station=3, station_name="Inactive", is_active=False),
            User(id_user=999, user_name="another-driver", password_hash="!test"),
        ])
        db.flush()
        for vehicle_id, owner, state, registration in [
            (VEHICLE_ID, client.user_id, "active", "OWN1"),
            (2, client.user_id, "inactive", "INACTIVE"),
            (3, 999, "active", "OTHER"),
        ]:
            db.add(Vehicle(
                id_vehicle=vehicle_id, id_user=owner, make="Example", model="Car",
                color="Blue", registration_number=registration, seat_capacity=4,
                vehicle_type="sedan", status=state,
            ))
        db.commit()
    departure = (datetime.now(timezone.utc) + timedelta(days=1)).replace(microsecond=123456)
    local = timezone(timedelta(hours=5, minutes=30))
    return {
        "id_vehicle": str(VEHICLE_ID),
        "id_source_station": 1,
        "id_destination_station": 2,
        "departure_time": departure.astimezone(local).isoformat(),
        "estimated_arrival_time": (departure + timedelta(hours=1)).astimezone(local).isoformat(),
        "total_seats": 3,
        "price_per_seat": "125.50",
        "notes": "  Office commute  ",
    }


def ride_count(client):
    with client.session() as db:
        return db.execute(text("SELECT COUNT(*) FROM ride")).scalar_one()


def offer(client, data, token=None):
    return client.post(URL, json=data, headers=auth(token or login(client)))


def test_offer_persists_token_driver_and_server_owned_fields(client, ride_data):
    response = offer(client, ride_data)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["id_driver"] == str(client.user_id)
    assert body["id_vehicle"] == str(VEHICLE_ID)
    assert isinstance(body["id_ride"], str)
    assert body["available_seats"] == body["total_seats"] == 3
    assert body["status"] == "open" and body["version"] == 1
    assert body["notes"] == "Office commute"
    assert body["price_per_seat"] == "125.50"
    expected = datetime.fromisoformat(ride_data["departure_time"]).astimezone(timezone.utc)
    expected = expected.replace(microsecond=123000)
    assert datetime.fromisoformat(body["departure_time"]) == expected
    assert body["created_at"].endswith("Z") and body["updated_at"].endswith("Z")
    with client.session() as db:
        row = db.execute(text(
            "SELECT id_driver, id_vehicle, total_seats, available_seats, status, version, "
            "cancel_reason, cancelled_at FROM ride WHERE id_ride = :i"
        ), {"i": int(body["id_ride"])}).one()
        assert tuple(row) == (client.user_id, VEHICLE_ID, 3, 3, "open", 1, None, None)


def test_minimal_offer_defaults_and_unique_ids(client, ride_data):
    for field in ("estimated_arrival_time", "notes", "price_per_seat"):
        ride_data.pop(field)
    first, second = offer(client, ride_data), offer(client, ride_data)
    assert first.status_code == second.status_code == 201
    body = first.json()
    assert body["estimated_arrival_time"] is None and body["notes"] is None
    assert Decimal(body["price_per_seat"]) == Decimal("0.00")
    assert body["id_ride"] != second.json()["id_ride"]
    assert ride_count(client) == 2


@pytest.mark.parametrize("patch", [
    {"id_source_station": 0}, {"id_destination_station": -1},
    {"id_source_station": 2**32}, {"id_vehicle": 2**64}, {"id_vehicle": True},
    {"id_destination_station": 1}, {"total_seats": 0}, {"total_seats": 9},
    {"total_seats": True}, {"total_seats": 1.5},
    {"price_per_seat": "-0.01"}, {"price_per_seat": "1.001"},
    {"price_per_seat": "100000000.00"}, {"price_per_seat": "NaN"},
    {"notes": "x" * 501},
    {"departure_time": "2030-01-01T12:00:00"},
    {"departure_time": "2000-01-01T12:00:00Z", "estimated_arrival_time": None},
    {"estimated_arrival_time": "2000-01-01T12:00:00Z"},
    {"id_driver": "999"}, {"available_seats": 1}, {"status": "completed"},
])
def test_invalid_offer_422_without_inserting(client, ride_data, patch):
    response = offer(client, ride_data | patch)
    assert response.status_code == 422, response.text
    assert ride_count(client) == 0


@pytest.mark.parametrize("field", ["id_vehicle", "id_source_station", "id_destination_station", "departure_time", "total_seats"])
def test_required_fields(client, ride_data, field):
    ride_data.pop(field)
    assert offer(client, ride_data).status_code == 422
    assert ride_count(client) == 0


def test_arrival_must_follow_departure_at_millisecond_precision(client, ride_data):
    ride_data["estimated_arrival_time"] = ride_data["departure_time"]
    assert offer(client, ride_data).status_code == 422


@pytest.mark.parametrize("patch, code", [
    ({"id_vehicle": "3"}, 404), ({"id_vehicle": "404"}, 404),
    ({"id_vehicle": "2"}, 422), ({"total_seats": 5}, 422),
    ({"id_source_station": 404}, 404), ({"id_destination_station": 404}, 404),
    ({"id_source_station": 3}, 404), ({"id_destination_station": 3}, 404),
])
def test_vehicle_and_station_validation(client, ride_data, patch, code):
    assert offer(client, ride_data | patch).status_code == code
    assert ride_count(client) == 0
    assert offer(client, ride_data).status_code == 201


@pytest.mark.parametrize("case, expected", [
    ("missing", "token_missing"), ("invalid", "token_invalid"),
    ("expired", "token_expired"), ("revoked", "session_revoked"),
    ("blocked", "account_inactive"), ("session_expired", "session_expired"),
])
def test_authentication_is_enforced(client, ride_data, case, expected):
    token = login(client)
    headers = auth(token)
    if case == "missing":
        headers = {}
    elif case == "invalid":
        headers = {"Authorization": "Bearer invalid.jwt.token"}
    elif case == "expired":
        past = datetime.now(timezone.utc) - timedelta(minutes=1)
        stale = jwt.encode({"sub": str(client.user_id), "sid": token["sessionId"], "exp": past}, settings.JWT_SECRET, algorithm="HS256")
        headers = {"Authorization": f"Bearer {stale}"}
    elif case == "revoked":
        client.post("/v1/auth/logout", headers=headers)
    else:
        with client.session() as db:
            if case == "blocked":
                db.execute(text("UPDATE user SET status = 'blocked' WHERE id_user = :i"), {"i": client.user_id})
            else:
                db.execute(text("UPDATE user_session SET expires_at = '2000-01-01' WHERE id_session = :i"), {"i": int(token["sessionId"])})
            db.commit()
    response = client.post(URL, json=ride_data, headers=headers)
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == expected
    assert response.headers["www-authenticate"] == "Bearer"
    assert ride_count(client) == 0


def test_insert_conflict_rolls_back(client, ride_data, monkeypatch):
    first = offer(client, ride_data)
    assert first.status_code == 201
    with monkeypatch.context() as context:
        context.setattr("app.services.ride_service.new_id", lambda: int(first.json()["id_ride"]))
        response = offer(client, ride_data)
    assert response.status_code == 409
    assert ride_count(client) == 1
    assert offer(client, ride_data).status_code == 201


def test_swagger_documents_bearer_security_and_server_fields():
    schema = app.openapi()
    endpoint = schema["paths"][URL]["post"]
    assert endpoint["security"] == [{"AccessToken": []}]
    request = schema["components"]["schemas"]["OfferRideRequest"]
    assert "id_vehicle" in request["required"]
    assert "id_driver" not in request["properties"]
    assert "available_seats" not in request["properties"]


def test_offer_with_real_mysql_transaction(mysql_database):
    from alembic import command
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import Session
    from app.db.session import get_db

    engine, config = mysql_database
    command.upgrade(config, "head")

    def get_test_db():
        with Session(engine) as db:
            yield db

    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = get_test_db
    live = TestClient(app)
    try:
        credentials = {"email": "driver@example.com", "phone": "+971502345678", "password": "Secret123"}
        created = live.post("/v1/auth/register", json=credentials)
        assert created.status_code == 201, created.text
        driver_id = int(created.json()["userId"])
        token = live.post("/v1/auth/login", json={"email": credentials["email"], "password": credentials["password"]}).json()
        with Session(engine) as db:
            db.add_all([
                Station(id_station=1, station_name="Source"),
                Station(id_station=2, station_name="Destination"),
                Vehicle(id_vehicle=VEHICLE_ID, id_user=driver_id, make="Example", model="Car", color="Blue", registration_number="TEST", seat_capacity=4, vehicle_type="sedan"),
            ])
            db.commit()
        departure = datetime.now(timezone.utc) + timedelta(days=1)
        data = {
            "id_vehicle": str(VEHICLE_ID), "id_source_station": 1, "id_destination_station": 2,
            "departure_time": departure.isoformat(), "total_seats": 4, "price_per_seat": "99999999.99",
        }
        response = live.post(URL, json=data, headers=auth(token))
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["id_driver"] == str(driver_id)
        assert body["available_seats"] == 4 and body["price_per_seat"] == "99999999.99"
        with Session(engine) as db:
            from app.models import Ride
            ride = db.get(Ride, int(body["id_ride"]))
            assert ride.id_driver == driver_id and ride.id_vehicle == VEHICLE_ID
            assert ride.price_per_seat == Decimal("99999999.99")
            assert ride.departure_time == departure.replace(tzinfo=None, microsecond=(departure.microsecond // 1000) * 1000)
        rejected = live.post(URL, json=data | {"id_destination_station": 999}, headers=auth(token))
        assert rejected.status_code == 404
        with Session(engine) as db:
            assert db.execute(text("SELECT COUNT(*) FROM ride")).scalar_one() == 1
    finally:
        live.close()
        if previous is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous
