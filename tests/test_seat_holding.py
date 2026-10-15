"""A pending request holds its seats until it is rejected or cancelled (or expires); these cover the ride
lifecycle paths (edit seats, expire, start) that must agree with that rule."""
from datetime import timedelta

from sqlalchemy import text

from app.models import Vehicle
from tests.test_auth_login import auth, client, login  # noqa: F401 (client is a fixture)
from tests.test_book_ride import now
from tests.test_booking_actions import (  # noqa: F401 (fixtures)
    RIDE,
    booking_status,
    driver,
    make_user,
    request_seats,
    ride_row,
    rider,
    stranger,
)


def add_vehicle(client):
    with client.session() as db:
        db.add(Vehicle(id_vehicle=1, id_user=client.user_id, make="Toyota", model="Corolla", color="White",
                       registration_number="SEAT1", seat_capacity=8, vehicle_type="sedan", status="active"))
        db.commit()


def depart_in_the_past(client):
    with client.session() as db:
        db.execute(text("UPDATE ride SET departure_time = :t"), {"t": now() - timedelta(minutes=5)})
        db.commit()


def test_editing_total_seats_counts_pending_requests(client, driver, rider):
    add_vehicle(client)
    request_seats(client, rider, seats=2)  # 4 seats, 3 free before: now 2 held, 1 free
    r = client.patch(f"/v1/rides/{RIDE}", json={"total_seats": 6}, headers=driver)
    assert r.status_code == 200, r.text
    assert (r.json()["total_seats"], r.json()["available_seats"], r.json()["status"]) == (6, 4, "open")  # 6 - 2 held
    r = client.patch(f"/v1/rides/{RIDE}", json={"total_seats": 2}, headers=driver)
    assert r.status_code == 200, r.text
    assert (r.json()["available_seats"], r.json()["status"]) == (0, "full")  # all 2 seats held by the request


def test_cannot_shrink_the_ride_below_the_seats_pending_requests_hold(client, driver, rider):
    add_vehicle(client)
    request_seats(client, rider, seats=3)
    r = client.patch(f"/v1/rides/{RIDE}", json={"total_seats": 2}, headers=driver)
    assert r.status_code == 409 and "held" in r.json()["detail"]
    assert ride_row(client)[:2] == (0, "full")  # untouched


def test_expiring_requests_gives_their_seats_back(client, driver, rider, stranger):
    a, b = request_seats(client, rider, seats=2), request_seats(client, stranger, seats=1)
    assert ride_row(client)[:2] == (0, "full")
    depart_in_the_past(client)
    r = client.post(f"/v1/rides/{RIDE}/expire-requests", headers=driver)
    assert r.status_code == 200 and r.json() == {"expired": 2}
    assert booking_status(client, a) == booking_status(client, b) == "expired"
    assert ride_row(client)[0] == 3  # everything held was released
    assert client.post(f"/v1/rides/{RIDE}/expire-requests", headers=driver).json() == {"expired": 0}  # safe to repeat
    assert ride_row(client)[0] == 3


def test_starting_the_ride_expires_pending_requests_and_releases_their_seats(client, driver, rider):
    b = request_seats(client, rider, seats=2)
    depart_in_the_past(client)
    r = client.post(f"/v1/rides/{RIDE}/start", headers=driver)
    assert r.status_code == 200, r.text
    assert booking_status(client, b) == "expired"
    assert (r.json()["status"], r.json()["available_seats"]) == ("started", 3)


def test_cancelling_the_ride_cancels_requests_and_frees_all_seats(client, driver, rider):
    b = request_seats(client, rider, seats=2)
    r = client.post(f"/v1/rides/{RIDE}/cancel", headers=driver)
    assert r.status_code == 200, r.text
    assert booking_status(client, b) == "cancelled_by_driver"
    assert (r.json()["status"], r.json()["available_seats"]) == ("cancelled", 4)
