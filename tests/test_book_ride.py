from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import text

from tests.test_auth_login import auth, client, login  # noqa: F401 (client is a fixture)

URL = "/v1/ride/booking"
DRIVER = 999
RIDE = 2**53 + 7  # beyond JS safe-integer range: IDs travel as strings


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def insert_ride(client, id_ride=RIDE, *, driver=DRIVER, seats=3, status="open", depart=None, price="25.50"):
    with client.session() as db:
        for sid, name in ((1, "Source"), (2, "Destination")):
            db.execute(text("INSERT OR IGNORE INTO station (id_station, station_name) VALUES (:i, :n)"), {"i": sid, "n": name})
        db.execute(
            text(
                "INSERT INTO ride (id_ride, id_driver, id_vehicle, id_source_station, id_destination_station, "
                "departure_time, total_seats, available_seats, price_per_seat, status, version) "
                "VALUES (:r, :d, 1, 1, 2, :t, 4, :s, :p, :st, 1)"
            ),
            {"r": id_ride, "d": driver, "t": depart or now() + timedelta(days=1), "s": seats, "p": price, "st": status},
        )
        db.commit()


@pytest.fixture
def ride(client):
    insert_ride(client)
    return RIDE


def book(client, body, token=None):
    return client.post(URL, json=body, headers=auth(token or login(client)))


def bookings(client):
    with client.session() as db:
        return db.execute(text("SELECT * FROM ride_booking")).mappings().all()


def test_book_creates_requested_booking(client, ride):
    r = book(client, {"id_ride": str(ride), "seats": 2, "rider_note": "  Two bags "})
    assert r.status_code == 201, r.text
    b = r.json()
    assert b["id_ride"] == str(ride) and b["id_rider"] == str(client.user_id) and b["id_driver"] == str(DRIVER)
    assert b["seats_booked"] == 2 and b["status"] == "requested" and b["version"] == 1
    assert b["price_per_seat"] == "25.50" and b["total_amount"] == "51.00"
    assert b["rider_note"] == "Two bags"
    assert b["created_at"].endswith("Z")
    (row,) = bookings(client)
    assert (row["id_rider"], row["seats_booked"], row["status"]) == (client.user_id, 2, "requested")


def test_a_request_holds_its_seats_straight_away(client, ride):
    assert book(client, {"id_ride": ride, "seats": 2}).status_code == 201
    with client.session() as db:
        assert db.execute(text("SELECT available_seats, status FROM ride")).one() == (1, "open")


def test_a_request_for_the_last_free_seats_makes_the_ride_full(client, ride):
    assert book(client, {"id_ride": ride, "seats": 3}).status_code == 201
    with client.session() as db:
        assert db.execute(text("SELECT available_seats, status FROM ride")).one() == (0, "full")


def test_price_is_a_snapshot_at_booking_time(client, ride):
    book(client, {"id_ride": ride, "seats": 1})
    with client.session() as db:
        db.execute(text("UPDATE ride SET price_per_seat = 99"))
        db.commit()
    assert Decimal(str(bookings(client)[0]["price_per_seat"])) == Decimal("25.5")


def test_requires_login(client, ride):
    assert client.post(URL, json={"id_ride": ride, "seats": 1}).status_code == 401
    assert bookings(client) == []


def test_unknown_ride_404(client):
    assert book(client, {"id_ride": 12345, "seats": 1}).status_code == 404


def test_cannot_book_own_ride_403(client):
    insert_ride(client, driver=client.user_id)
    assert book(client, {"id_ride": RIDE, "seats": 1}).status_code == 403
    assert bookings(client) == []


@pytest.mark.parametrize("status", ["full", "started", "completed", "cancelled"])
def test_ride_must_be_open_409(client, status):
    insert_ride(client, status=status)
    r = book(client, {"id_ride": RIDE, "seats": 1})
    assert r.status_code == 409 and r.json()["detail"] == "ride is not open for booking"


def test_departed_ride_409(client):
    insert_ride(client, depart=now() - timedelta(minutes=1))
    assert book(client, {"id_ride": RIDE, "seats": 1}).status_code == 409


def test_not_enough_seats_409(client):
    insert_ride(client, seats=2)
    r = book(client, {"id_ride": RIDE, "seats": 3})
    assert r.status_code == 409 and r.json()["detail"] == "not enough seats: 2 available"
    assert book(client, {"id_ride": RIDE, "seats": 2}).status_code == 201  # exactly the free seats is fine


def test_duplicate_active_booking_409_but_rebook_after_cancel(client, ride):
    token = login(client)
    assert book(client, {"id_ride": ride, "seats": 1}, token).status_code == 201
    r = book(client, {"id_ride": ride, "seats": 1}, token)
    assert r.status_code == 409 and "already have an active booking" in r.json()["detail"]
    with client.session() as db:
        db.execute(text("UPDATE ride_booking SET status = 'cancelled_by_rider'"))
        db.commit()
    assert book(client, {"id_ride": ride, "seats": 1}, token).status_code == 201
    assert len(bookings(client)) == 2


@pytest.mark.parametrize(
    "body",
    [
        {"seats": 1},
        {"id_ride": RIDE},
        {"id_ride": RIDE, "seats": 0},
        {"id_ride": RIDE, "seats": 9},
        {"id_ride": RIDE, "seats": True},
        {"id_ride": RIDE, "seats": 1.5},
        {"id_ride": RIDE, "seats": "2"},
        {"id_ride": 0, "seats": 1},
        {"id_ride": -5, "seats": 1},
        {"id_ride": True, "seats": 1},
        {"id_ride": 2**64, "seats": 1},
        {"id_ride": "abc", "seats": 1},
        {"id_ride": RIDE, "seats": 1, "rider_note": "x" * 256},
        {"id_ride": RIDE, "seats": 1, "id_rider": 5},
        {"id_ride": RIDE, "seats": 1, "status": "accepted"},
        {"id_ride": RIDE, "seats": 1, "total_amount": "0"},
    ],
)
def test_invalid_request_422_without_inserting(client, ride, body):
    assert book(client, body).status_code == 422
    assert bookings(client) == []
