from datetime import timedelta

import pytest
from sqlalchemy import text

from tests.test_auth_login import USER, auth, client, login  # noqa: F401 (client is a fixture)
from tests.test_book_ride import insert_ride, now

RIDE = 2**53 + 11  # beyond JS safe-integer range: IDs travel as strings


@pytest.fixture
def driver(client):
    """The `client` user (jane) is the driver of RIDE."""
    insert_ride(client, RIDE, driver=client.user_id, seats=3)
    return auth(login(client))


def make_user(client, email, phone):
    uid = int(client.post("/v1/auth/register", json={"email": email, "phone": phone, "password": "Secret123"}).json()["userId"])
    token = client.post("/v1/auth/login", json={"email": email, "password": "Secret123"}).json()
    return {"id": uid, "headers": auth(token)}


@pytest.fixture
def rider(client, driver):
    return make_user(client, "rider@example.com", "+971504444444")


@pytest.fixture
def stranger(client, driver):
    return make_user(client, "stranger@example.com", "+971505555555")


def request_seats(client, who, seats=1, ride=RIDE):
    r = client.post("/v1/ride/booking", json={"id_ride": ride, "seats": seats}, headers=who["headers"])
    assert r.status_code == 201, r.text
    return r.json()["id_booking"]


def approve(client, headers, id_booking):
    return client.post(f"/v1/ride/booking/{id_booking}/approve", headers=headers)


def cancel(client, headers, id_booking, body=None):
    return client.post(f"/v1/ride/booking/{id_booking}/cancel", headers=headers, json=body) if body is not None else client.post(
        f"/v1/ride/booking/{id_booking}/cancel", headers=headers
    )


def ride_row(client, ride=RIDE):
    with client.session() as db:
        return db.execute(text("SELECT available_seats, status, version FROM ride WHERE id_ride = :r"), {"r": ride}).one()


def booking_status(client, id_booking):
    with client.session() as db:
        return db.execute(text("SELECT status FROM ride_booking WHERE id_booking = :b"), {"b": int(id_booking)}).scalar_one()


# ===================== approve =====================


def test_approving_keeps_the_seats_already_held(client, driver, rider):
    b = request_seats(client, rider, seats=2)
    assert ride_row(client)[:2] == (1, "open")  # the request already holds its 2 seats
    r = approve(client, driver, b)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "accepted" and body["id_booking"] == b and body["version"] == 2
    assert body["responded_at"].endswith("Z") and body["cancelled_at"] is None and body["cancel_reason"] is None
    assert ride_row(client)[:2] == (1, "open")  # approving takes nothing more


def test_requests_hold_seats_so_the_ride_becomes_full(client, driver, rider, stranger):
    first, second = request_seats(client, rider, seats=2), request_seats(client, stranger, seats=1)
    assert ride_row(client)[:2] == (0, "full")  # 3 seats, all held by pending requests
    assert approve(client, driver, first).status_code == 200  # approving a request on a full ride is fine
    assert approve(client, driver, second).status_code == 200
    assert ride_row(client)[:2] == (0, "full")


def test_requests_cannot_add_up_to_more_than_the_free_seats(client, driver, rider, stranger):
    first = request_seats(client, rider, seats=2)  # 3 seats: 2 held, 1 free
    r = client.post("/v1/ride/booking", json={"id_ride": RIDE, "seats": 2}, headers=stranger["headers"])
    assert r.status_code == 409 and r.json()["detail"] == "not enough seats: 1 available"
    assert ride_row(client)[:2] == (1, "open")  # the refused request held nothing
    assert request_seats(client, stranger, seats=1)  # exactly the free seat is fine
    assert ride_row(client)[:2] == (0, "full")
    third = make_user(client, "third@example.com", "+971507777777")
    r = client.post("/v1/ride/booking", json={"id_ride": RIDE, "seats": 1}, headers=third["headers"])
    assert r.status_code == 409 and r.json()["detail"] == "ride is not open for booking"
    assert booking_status(client, first) == "requested"


def test_seats_free_up_for_others_when_a_request_is_cancelled_or_rejected(client, driver, rider, stranger):
    mine = request_seats(client, rider, seats=3)  # takes all 3 seats
    assert ride_row(client)[:2] == (0, "full")
    assert client.post("/v1/ride/booking", json={"id_ride": RIDE, "seats": 1}, headers=stranger["headers"]).status_code == 409
    assert cancel(client, rider["headers"], mine).status_code == 200  # cancelled: seats are free again
    assert ride_row(client)[:2] == (3, "open")
    theirs = request_seats(client, stranger, seats=3)
    assert ride_row(client)[:2] == (0, "full")
    assert client.post(f"/v1/ride/booking/{theirs}/reject", headers=driver).status_code == 200  # rejected: free again
    assert ride_row(client)[:2] == (3, "open")
    assert request_seats(client, rider, seats=3)  # and the first rider can take them after all
    assert ride_row(client)[:2] == (0, "full")


def test_rider_cannot_approve_own_request_403(client, driver, rider):
    b = request_seats(client, rider)
    r = approve(client, rider["headers"], b)
    assert r.status_code == 403
    assert booking_status(client, b) == "requested" and ride_row(client)[0] == 2  # its 1 seat is still held


def test_stranger_and_unknown_booking_404(client, driver, rider, stranger):
    b = request_seats(client, rider)
    assert approve(client, stranger["headers"], b).status_code == 404  # existence is not revealed
    assert approve(client, driver, 123456789).status_code == 404
    assert booking_status(client, b) == "requested"


def test_approve_requires_login(client, driver, rider):
    b = request_seats(client, rider)
    assert client.post(f"/v1/ride/booking/{b}/approve").status_code == 401


@pytest.mark.parametrize("state", ["accepted", "rejected", "cancelled_by_rider", "cancelled_by_driver", "completed", "expired"])
def test_only_requested_bookings_can_be_approved(client, driver, rider, state):
    b = request_seats(client, rider)
    with client.session() as db:
        db.execute(text("UPDATE ride_booking SET status = :s"), {"s": state})
        db.commit()
    r = approve(client, driver, b)
    assert r.status_code == 409 and state in r.json()["detail"]
    assert ride_row(client)[0] == 2  # a refused approval changes nothing


def test_approving_twice_does_not_take_seats_twice(client, driver, rider):
    b = request_seats(client, rider, seats=2)
    assert approve(client, driver, b).status_code == 200
    assert approve(client, driver, b).status_code == 409
    assert ride_row(client)[0] == 1


@pytest.mark.parametrize("ride_status", ["started", "completed", "cancelled"])
def test_cannot_approve_on_a_ride_that_is_not_open(client, driver, rider, ride_status):
    b = request_seats(client, rider)
    with client.session() as db:
        db.execute(text("UPDATE ride SET status = :s"), {"s": ride_status})
        db.commit()
    assert approve(client, driver, b).status_code == 409


def test_cannot_approve_after_departure(client, driver, rider):
    b = request_seats(client, rider)
    with client.session() as db:
        db.execute(text("UPDATE ride SET departure_time = :t"), {"t": now() - timedelta(minutes=1)})
        db.commit()
    assert approve(client, driver, b).status_code == 409
    assert booking_status(client, b) == "requested"


@pytest.mark.parametrize("bad", ["0", "-1", "abc", str(2**64)])
def test_invalid_booking_id_422(client, driver, bad):
    assert approve(client, driver, bad).status_code == 422
    assert cancel(client, driver, bad).status_code == 422


# ===================== cancel =====================


def test_rider_cancels_pending_request(client, driver, rider):
    b = request_seats(client, rider, seats=2)
    assert ride_row(client)[:2] == (1, "open")  # the pending request holds 2 seats
    r = cancel(client, rider["headers"], b, {"reason": "  plans changed "})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "cancelled_by_rider" and body["cancel_reason"] == "plans changed"
    assert body["cancelled_at"].endswith("Z") and body["responded_at"] is None
    assert ride_row(client)[:2] == (3, "open")  # the seats it held are free again


def test_cancel_without_body_is_fine(client, driver, rider):
    b = request_seats(client, rider)
    r = cancel(client, rider["headers"], b)
    assert r.status_code == 200 and r.json()["cancel_reason"] is None


def test_rider_cancelling_an_accepted_booking_gives_seats_back(client, driver, rider):
    b = request_seats(client, rider, seats=2)
    approve(client, driver, b)
    assert ride_row(client)[0] == 1
    r = cancel(client, rider["headers"], b)
    assert r.status_code == 200 and r.json()["status"] == "cancelled_by_rider"
    assert ride_row(client)[:2] == (3, "open")


def test_full_ride_reopens_when_an_accepted_booking_is_cancelled(client, driver, rider, stranger):
    a, c = request_seats(client, rider, seats=2), request_seats(client, stranger, seats=1)
    approve(client, driver, a)
    approve(client, driver, c)
    assert ride_row(client)[:2] == (0, "full")
    assert cancel(client, stranger["headers"], c).status_code == 200
    assert ride_row(client)[:2] == (1, "open")


def test_driver_can_cancel_a_passenger(client, driver, rider):
    b = request_seats(client, rider, seats=1)
    approve(client, driver, b)
    r = cancel(client, driver, b, {"reason": "car trouble"})
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled_by_driver" and r.json()["cancel_reason"] == "car trouble"
    assert ride_row(client)[:2] == (3, "open")


def test_driver_can_cancel_a_pending_request(client, driver, rider):
    b = request_seats(client, rider)
    assert cancel(client, driver, b).json()["status"] == "cancelled_by_driver"


def test_seats_never_exceed_total_when_restored(client, driver, rider):
    b = request_seats(client, rider, seats=3)
    approve(client, driver, b)
    with client.session() as db:  # corrupt-ish data: ride already shows all seats free
        db.execute(text("UPDATE ride SET available_seats = 4"))
        db.commit()
    cancel(client, rider["headers"], b)
    assert ride_row(client)[0] == 4  # capped at total_seats (4), not 7


def test_stranger_unknown_and_logged_out_cannot_cancel(client, driver, rider, stranger):
    b = request_seats(client, rider)
    assert cancel(client, stranger["headers"], b).status_code == 404
    assert cancel(client, driver, 123456789).status_code == 404
    assert client.post(f"/v1/ride/booking/{b}/cancel").status_code == 401
    assert booking_status(client, b) == "requested"


@pytest.mark.parametrize("state", ["rejected", "cancelled_by_rider", "cancelled_by_driver", "completed", "expired"])
def test_only_active_bookings_can_be_cancelled(client, driver, rider, state):
    b = request_seats(client, rider)
    with client.session() as db:
        db.execute(text("UPDATE ride_booking SET status = :s"), {"s": state})
        db.commit()
    r = cancel(client, rider["headers"], b)
    assert r.status_code == 409 and state in r.json()["detail"]


def test_cancelling_twice_does_not_return_seats_twice(client, driver, rider):
    b = request_seats(client, rider, seats=2)
    approve(client, driver, b)
    assert cancel(client, rider["headers"], b).status_code == 200
    assert cancel(client, rider["headers"], b).status_code == 409
    assert ride_row(client)[0] == 3


@pytest.mark.parametrize("ride_status", ["started", "completed", "cancelled"])
def test_cannot_cancel_once_the_ride_has_started(client, driver, rider, ride_status):
    b = request_seats(client, rider)
    with client.session() as db:
        db.execute(text("UPDATE ride SET status = :s"), {"s": ride_status})
        db.commit()
    r = cancel(client, rider["headers"], b)
    assert r.status_code == 409 and booking_status(client, b) == "requested"


@pytest.mark.parametrize("body", [{"reason": "x" * 256}, {"reason": "ok", "status": "accepted"}, {"seats": 1}])
def test_invalid_cancel_body_422(client, driver, rider, body):
    b = request_seats(client, rider)
    assert cancel(client, rider["headers"], b, body).status_code == 422
    assert booking_status(client, b) == "requested"


# ===================== lifecycle =====================


def test_rider_can_book_again_after_cancelling(client, driver, rider):
    b = request_seats(client, rider)
    cancel(client, rider["headers"], b)
    second = request_seats(client, rider)
    assert second != b


def test_my_lists_reflect_approval_and_cancellation(client, driver, rider):
    b = request_seats(client, rider, seats=2)
    approve(client, driver, b)
    mine = client.get("/v1/me/bookings", headers=rider["headers"]).json()["items"]
    assert [(i["id_booking"], i["status"], i["ride"]["available_seats"]) for i in mine] == [(b, "accepted", 1)]
    offered = client.get("/v1/me/rides", headers=driver).json()["items"][0]
    assert offered["requests"] == {"pending_requests": 0, "accepted_seats": 2}
    cancel(client, rider["headers"], b)
    assert client.get("/v1/me/bookings", headers=rider["headers"]).json()["items"] == []  # no longer upcoming
    past = client.get("/v1/me/bookings", headers=rider["headers"], params={"when": "past"}).json()["items"]
    assert [i["status"] for i in past] == ["cancelled_by_rider"]
