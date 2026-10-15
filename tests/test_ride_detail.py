from datetime import timedelta

import pytest
from sqlalchemy import text

from app.models import Vehicle
from tests.test_auth_login import auth, client, login  # noqa: F401 (client is a fixture)
from tests.test_booking_actions import make_user
from tests.test_my_rides import OTHER, Data, hrs

URL = "/v1/rides/{}"


@pytest.fixture
def d(client):
    return Data(client)


@pytest.fixture
def rider(client):
    u = make_user(client, "rider@example.com", "+971504444444")
    with client.session() as db:
        db.execute(text("INSERT INTO user_profile (id_user, full_name, photo_url) VALUES (:i, 'Rita Rider', 'http://x/rita.png')"), {"i": u["id"]})
        db.commit()
    return u


@pytest.fixture
def rider2(client):
    u = make_user(client, "rider2@example.com", "+971505555555")
    with client.session() as db:
        db.execute(text("INSERT INTO user_profile (id_user, full_name) VALUES (:i, 'Sam Second')"), {"i": u["id"]})
        db.commit()
    return u


def detail(client, id_ride, headers=None):
    return client.get(URL.format(id_ride), headers=headers or auth(login(client)))


def set_created(client, id_booking, when):
    with client.session() as db:
        db.execute(text("UPDATE ride_booking SET created_at = :t WHERE id_booking = :b"), {"t": when, "b": int(id_booking)})
        db.commit()


# ---------- viewer ----------


def test_viewer_sees_open_ride_details_without_private_data(client, d):
    ride = d.ride(driver=OTHER, depart=hrs(5), seats=2)
    d.booking(ride, rider=777)  # someone else's booking must not leak
    r = detail(client, ride)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id_ride"] == ride and isinstance(body["id_ride"], str)
    assert body["role"] == "viewer" and body["status"] == "open"
    assert body["source"] == {"id_station": 1, "name": "Alpha"} and body["destination"] == {"id_station": 2, "name": "Beta"}
    assert body["total_seats"] == 4 and body["available_seats"] == 2 and body["price_per_seat"] == "20.00"
    assert body["driver"] == {"id_user": str(OTHER), "full_name": "Other Driver", "photo_url": None}
    assert body["departure_time"].endswith("Z") and body["vehicle"] is None
    assert body["my_booking"] is None and body["requests"] is None and body["bookings"] is None


def test_viewer_can_see_a_full_ride(client, d):
    ride = d.ride(driver=OTHER, depart=hrs(5), status="full", seats=0)
    r = detail(client, ride)
    assert r.status_code == 200 and r.json()["status"] == "full" and r.json()["role"] == "viewer"


@pytest.mark.parametrize("status", ["started", "completed", "cancelled"])
def test_viewer_cannot_see_rides_that_are_not_open_or_full(client, d, status):
    ride = d.ride(driver=OTHER, depart=hrs(5), status=status)
    assert detail(client, ride).status_code == 404


def test_vehicle_is_included_when_the_ride_has_one(client, d):
    with client.session() as db:
        db.add(Vehicle(id_vehicle=555, id_user=OTHER, make="Toyota", model="Corolla", color="White",
                       registration_number="ABC123", seat_capacity=4, vehicle_type="sedan", status="active"))
        db.commit()
    ride = d.ride(driver=OTHER, depart=hrs(5))
    with client.session() as db:
        db.execute(text("UPDATE ride SET id_vehicle = 555 WHERE id_ride = :r"), {"r": int(ride)})
        db.commit()
    assert detail(client, ride).json()["vehicle"] == {"make": "Toyota", "model": "Corolla", "color": "White", "vehicle_type": "sedan"}


# ---------- rider ----------


def test_rider_sees_their_booking_but_not_other_riders(client, d, rider, rider2):
    ride = d.ride(driver=OTHER, depart=hrs(6))
    mine = d.booking(ride, rider=rider["id"], seats=2, status="accepted")
    d.booking(ride, rider=rider2["id"], seats=1, status="requested")
    r = detail(client, ride, rider["headers"])
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["role"] == "rider"
    assert body["my_booking"] == {
        "id_booking": mine, "status": "accepted", "seats_booked": 2, "price_per_seat": "20.00",
        "total_amount": "40.00", "rider_note": "note", "created_at": body["my_booking"]["created_at"],
    }
    assert body["my_booking"]["created_at"].endswith("Z")
    assert body["requests"] is None and body["bookings"] is None  # riders never see each other


def test_rider_keeps_access_after_the_ride_is_done_or_cancelled(client, d, rider):
    done = d.ride(driver=OTHER, depart=hrs(-30), status="completed")
    d.booking(done, rider=rider["id"], status="completed")
    called_off = d.ride(driver=OTHER, depart=hrs(8), status="cancelled")
    d.booking(called_off, rider=rider["id"], status="cancelled_by_driver")
    for ride, booking_status in ((done, "completed"), (called_off, "cancelled_by_driver")):
        r = detail(client, ride, rider["headers"])
        assert r.status_code == 200 and r.json()["role"] == "rider" and r.json()["my_booking"]["status"] == booking_status


def test_my_booking_prefers_the_active_one_over_a_newer_cancelled_one(client, d, rider):
    ride = d.ride(driver=OTHER, depart=hrs(6))
    active = d.booking(ride, rider=rider["id"], status="requested")
    cancelled = d.booking(ride, rider=rider["id"], status="cancelled_by_rider")
    set_created(client, active, hrs(-3))
    set_created(client, cancelled, hrs(-1))  # newer, but not active
    assert detail(client, ride, rider["headers"]).json()["my_booking"]["id_booking"] == active


def test_my_booking_falls_back_to_the_latest_when_none_is_active(client, d, rider):
    ride = d.ride(driver=OTHER, depart=hrs(6))
    older = d.booking(ride, rider=rider["id"], status="rejected")
    newer = d.booking(ride, rider=rider["id"], status="cancelled_by_rider")
    set_created(client, older, hrs(-5))
    set_created(client, newer, hrs(-1))
    assert detail(client, ride, rider["headers"]).json()["my_booking"]["id_booking"] == newer


def test_someone_with_only_a_cancelled_booking_on_a_hidden_ride_is_still_a_participant(client, d, rider):
    ride = d.ride(driver=OTHER, depart=hrs(6), status="cancelled")
    d.booking(ride, rider=rider["id"], status="cancelled_by_driver")
    assert detail(client, ride, rider["headers"]).status_code == 200
    stranger = make_user(client, "s@example.com", "+971506666666")
    assert detail(client, ride, stranger["headers"]).status_code == 404


# ---------- driver ----------


def test_driver_sees_requests_and_passengers(client, d, rider, rider2):
    me = client.user_id
    ride = d.ride(driver=me, depart=hrs(6), seats=1)
    accepted = d.booking(ride, rider=rider["id"], seats=2, status="accepted")
    pending = d.booking(ride, rider=rider2["id"], seats=1, status="requested")
    d.booking(ride, rider=778, status="cancelled_by_rider")
    d.booking(ride, rider=779, status="rejected")
    r = detail(client, ride)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["role"] == "driver" and body["my_booking"] is None
    assert body["requests"] == {"pending_requests": 1, "accepted_seats": 2}
    assert [(b["id_booking"], b["status"], b["seats_booked"]) for b in body["bookings"]] == [
        (accepted, "accepted", 2), (pending, "requested", 1),
    ]
    first = body["bookings"][0]
    assert first["rider"] == {"id_user": str(rider["id"]), "full_name": "Rita Rider", "photo_url": "http://x/rita.png"}
    assert first["total_amount"] == "40.00" and first["rider_note"] == "note" and first["created_at"].endswith("Z")
    assert body["bookings"][1]["rider"]["full_name"] == "Sam Second"


def test_driver_without_any_bookings_gets_empty_lists(client, d):
    ride = d.ride(driver=client.user_id, depart=hrs(6))
    body = detail(client, ride).json()
    assert body["role"] == "driver" and body["bookings"] == []
    assert body["requests"] == {"pending_requests": 0, "accepted_seats": 0}


@pytest.mark.parametrize("status", ["started", "completed", "cancelled"])
def test_driver_can_always_see_their_own_ride(client, d, status):
    ride = d.ride(driver=client.user_id, depart=hrs(-4), status=status)
    r = detail(client, ride)
    assert r.status_code == 200 and r.json()["role"] == "driver" and r.json()["status"] == status


def test_a_rider_booking_does_not_make_someone_the_driver(client, d, rider):
    ride = d.ride(driver=client.user_id, depart=hrs(6))
    d.booking(ride, rider=rider["id"])
    assert detail(client, ride, rider["headers"]).json()["role"] == "rider"
    assert detail(client, ride).json()["role"] == "driver"


# ---------- errors ----------


def test_unknown_ride_404(client, d):
    assert detail(client, 123456789).status_code == 404


@pytest.mark.parametrize("bad", ["0", "-1", "abc", str(2**64), "1.5"])
def test_invalid_ride_id_422(client, d, bad):
    assert detail(client, bad).status_code == 422


def test_requires_login(client, d):
    ride = d.ride(driver=OTHER, depart=hrs(5))
    assert client.get(URL.format(ride)).status_code == 401
    assert client.get(URL.format(ride), headers={"Authorization": "Bearer nonsense"}).status_code == 401


def test_other_ride_routes_still_work(client, d):
    """GET /v1/rides (search) and POST /v1/rides/offer are unaffected by the /{id_ride} route."""
    assert client.get("/v1/rides", headers=auth(login(client))).status_code == 422  # missing required filters
    assert client.post("/v1/rides/offer", headers=auth(login(client)), json={}).status_code == 422
