from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from app.models import Ride, RideBooking, Station
from app.models.notification import NotificationType
from app.repositories.notification_repo import NotificationRepository
from app.services.notification_service import NotificationService
from tests.test_auth_login import auth, client, login  # noqa: F401  (client is a fixture)
from tests.test_vehicles import other_user_headers

URL = "/v1/notifications"
RIDE_ID = 123456789012345678


@pytest.fixture
def h(client):
    return auth(login(client))


def notify(client, id_user, message, type=NotificationType.booking_requested, id_booking=None):
    with client.session() as db:
        id_notification = NotificationService(NotificationRepository(db)).notify(
            id_user, type, RIDE_ID, message, id_booking=id_booking
        )
        db.commit()
    return str(id_notification)


def test_requires_session(client):
    assert client.get(URL).status_code == 401
    assert client.post(f"{URL}/1/read").status_code == 401


def test_empty(client, h):
    r = client.get(URL, headers=h)
    assert r.status_code == 200 and r.headers["cache-control"] == "no-store"
    assert r.json() == {"items": [], "unreadCount": 0}


def test_list_newest_first_with_fields(client, h):
    first = notify(client, client.user_id, "Rahul requested 2 seats on your 9:00 AM ride", id_booking=42)
    second = notify(client, client.user_id, "Your ride was cancelled", type=NotificationType.ride_cancelled)
    body = client.get(URL, headers=h).json()
    assert body["unreadCount"] == 2
    assert [n["idNotification"] for n in body["items"]] == [second, first]
    item = body["items"][1]
    assert item["type"] == "booking_requested" and item["idRide"] == str(RIDE_ID) and item["idBooking"] == "42"
    assert item["message"].startswith("Rahul") and item["createdAt"].endswith("Z")
    assert body["items"][0]["idBooking"] is None


def test_limit_keeps_total_count(client, h):
    for i in range(3):
        notify(client, client.user_id, f"n{i}")
    body = client.get(URL, params={"limit": 2}, headers=h).json()
    assert len(body["items"]) == 2 and body["unreadCount"] == 3
    assert client.get(URL, params={"limit": 0}, headers=h).status_code == 422


def test_mark_read_hides_it(client, h):
    keep = notify(client, client.user_id, "keep")
    read = notify(client, client.user_id, "read me")
    assert client.post(f"{URL}/{read}/read", headers=h).status_code == 204
    assert client.post(f"{URL}/{read}/read", headers=h).status_code == 204  # idempotent
    body = client.get(URL, headers=h).json()
    assert [n["idNotification"] for n in body["items"]] == [keep] and body["unreadCount"] == 1


def test_cannot_touch_other_users_notifications(client, h):
    other_h = other_user_headers(client)
    mine = notify(client, client.user_id, "mine")
    assert client.get(URL, headers=other_h).json()["unreadCount"] == 0
    assert client.post(f"{URL}/{mine}/read", headers=other_h).status_code == 404
    assert client.post(f"{URL}/999/read", headers=h).status_code == 404
    assert client.get(URL, headers=h).json()["unreadCount"] == 1


def test_mark_all_read(client, h):
    for i in range(2):
        notify(client, client.user_id, f"n{i}")
    r = client.post(f"{URL}/read-all", headers=h)
    assert r.status_code == 200 and r.json() == {"marked": 2}
    assert client.get(URL, headers=h).json() == {"items": [], "unreadCount": 0}


BOOKING_ID = 2**53 + 7
STRANGER_ID = 555


@pytest.fixture
def ride(client):
    """A ride driven by the logged-in user, booked by user 777."""
    with client.session() as db:
        db.add_all([Station(id_station=1, station_name="A"), Station(id_station=2, station_name="B")])
        db.flush()
        db.add(Ride(
            id_ride=RIDE_ID, id_driver=client.user_id, id_vehicle=1, id_source_station=1, id_destination_station=2,
            departure_time=datetime(2030, 1, 1, 9), total_seats=3, available_seats=3,
        ))
        db.flush()
        db.add(RideBooking(
            id_booking=BOOKING_ID, id_ride=RIDE_ID, id_rider=777, id_driver=client.user_id,
            seats_booked=2, price_per_seat=Decimal("10"), total_amount=Decimal("20"),
        ))
        db.commit()


def send_body(**kw):
    body = {"idUser": "777", "type": "booking_accepted", "idRide": str(RIDE_ID),
            "idBooking": str(BOOKING_ID), "message": "  Your 2 seats are confirmed  "}
    return {k: v for k, v in {**body, **kw}.items() if v is not ...}


def test_send_reaches_recipient(client, h, ride):
    r = client.post(URL, json=send_body(), headers=h)
    assert r.status_code == 201, r.text
    sent = r.json()
    assert sent["message"] == "Your 2 seats are confirmed" and sent["idBooking"] == str(BOOKING_ID)
    assert sent["type"] == "booking_accepted" and sent["createdAt"].endswith("Z")
    with client.session() as db:
        inbox = NotificationService(NotificationRepository(db)).unread(777, 20)
    assert [n.idNotification for n in inbox.items] == [sent["idNotification"]]
    assert client.get(URL, headers=h).json()["unreadCount"] == 0  # not in the sender's inbox


def test_send_without_booking(client, h, ride):
    r = client.post(URL, json=send_body(idBooking=..., type="ride_modified"), headers=h)
    assert r.status_code == 201 and r.json()["idBooking"] is None


@pytest.mark.parametrize("patch, code", [
    ({"idRide": "42"}, 404),
    ({"idBooking": "43"}, 404),
    ({"idUser": str(STRANGER_ID)}, 422),
    ({"message": "   "}, 422),
    ({"message": "x" * 256}, 422),
    ({"type": "hello"}, 422),
    ({"idUser": True}, 422),
    ({"extra": 1}, 422),
])
def test_send_validation(client, h, ride, patch, code):
    assert client.post(URL, json=send_body(**patch), headers=h).status_code == code
    with client.session() as db:
        assert NotificationService(NotificationRepository(db)).unread(777, 20).unreadCount == 0


def test_send_requires_sender_on_ride(client, ride):
    outsider = other_user_headers(client)
    r = client.post(URL, json=send_body(), headers=outsider)
    assert r.status_code == 403
    assert client.post(URL, json=send_body()).status_code == 401
