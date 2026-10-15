import pytest
from sqlalchemy import text

from app.repositories.notification_repo import NotificationRepository
from tests.test_auth_login import auth, client, login  # noqa: F401 (client is a fixture)
from tests.test_booking_actions import (  # noqa: F401 (fixtures)
    approve,
    booking_status,
    cancel,
    driver,
    make_user,
    request_seats,
    ride_row,
    rider,
    stranger,
)
from tests.test_offer_ride import offer, ride_data  # noqa: F401 (fixture)

RIDE = 2**53 + 11  # same ride id as the booking-action fixtures


def inbox(client, headers):
    r = client.get("/v1/notifications", headers=headers)
    assert r.status_code == 200, r.text
    return r.json()["items"]


def types(client, headers):
    return [n["type"] for n in inbox(client, headers)]


def reject(client, headers, id_booking, body=None):
    url = f"/v1/ride/booking/{id_booking}/reject"
    return client.post(url, headers=headers, json=body) if body is not None else client.post(url, headers=headers)


def name(client, user_id, full_name):
    with client.session() as db:
        db.execute(text("INSERT INTO user_profile (id_user, full_name) VALUES (:i, :n)"), {"i": user_id, "n": full_name})
        db.commit()


# ===================== booking requested =====================


def test_requesting_notifies_the_driver_only(client, driver, rider):
    b = request_seats(client, rider, seats=2)
    (n,) = inbox(client, driver)
    assert n["type"] == "booking_requested"
    assert n["idRide"] == str(RIDE) and n["idBooking"] == b
    assert n["message"].startswith("A rider requested 2 seats on your Source → Destination ride on ")
    assert n["message"].endswith(" UTC.")
    assert inbox(client, rider["headers"]) == []


def test_messages_use_profile_names_and_singular_seat(client, driver, rider):
    name(client, rider["id"], "Rita Rider")
    request_seats(client, rider, seats=1)
    (n,) = inbox(client, driver)
    assert n["message"].startswith("Rita Rider requested 1 seat on your ")  # "seat", not "seats"


# ===================== approved / rejected / cancelled =====================


def test_approving_notifies_the_rider(client, driver, rider):
    name(client, client.user_id, "Dina Driver")
    b = request_seats(client, rider, seats=2)
    assert approve(client, driver, b).status_code == 200
    (n,) = inbox(client, rider["headers"])
    assert n["type"] == "booking_accepted" and n["idBooking"] == b and n["idRide"] == str(RIDE)
    assert n["message"].startswith("Dina Driver approved your request for 2 seats on the Source → Destination ride")
    assert types(client, driver) == ["booking_requested"]  # the driver is not told about their own action


def test_rejecting_notifies_the_rider_with_the_reason(client, driver, rider):
    b = request_seats(client, rider)
    assert reject(client, driver, b, {"reason": "no room for luggage"}).status_code == 200
    (n,) = inbox(client, rider["headers"])
    assert n["type"] == "booking_rejected" and n["idBooking"] == b
    assert "declined your request for 1 seat" in n["message"] and n["message"].endswith("Reason: no room for luggage")


def test_rejecting_without_a_reason_has_no_reason_text(client, driver, rider):
    b = request_seats(client, rider)
    reject(client, driver, b)
    assert "Reason" not in inbox(client, rider["headers"])[0]["message"]


def test_rider_cancelling_notifies_the_driver(client, driver, rider):
    name(client, rider["id"], "Rita Rider")
    b = request_seats(client, rider, seats=2)
    approve(client, driver, b)
    assert cancel(client, rider["headers"], b, {"reason": "plans changed"}).status_code == 200
    assert types(client, driver) == ["booking_cancelled", "booking_requested"]  # newest first
    cancelled = inbox(client, driver)[0]
    assert cancelled["message"].startswith("Rita Rider cancelled their booking of 2 seats on your ")
    assert cancelled["message"].endswith("Reason: plans changed")
    assert types(client, rider["headers"]) == ["booking_accepted"]  # the canceller gets nothing new


def test_driver_cancelling_notifies_the_rider(client, driver, rider):
    name(client, client.user_id, "Dina Driver")
    b = request_seats(client, rider)
    approve(client, driver, b)
    assert cancel(client, driver, b, {"reason": "car trouble"}).status_code == 200
    first = inbox(client, rider["headers"])[0]
    assert first["type"] == "booking_cancelled"
    assert first["message"].startswith("Dina Driver cancelled your booking of 1 seat on the ")
    assert first["message"].endswith("Reason: car trouble")
    assert types(client, driver) == ["booking_requested"]


def test_cancelling_a_pending_request_also_notifies(client, driver, rider):
    b = request_seats(client, rider)
    cancel(client, rider["headers"], b)
    assert types(client, driver) == ["booking_cancelled", "booking_requested"]


# ===================== ride created =====================


def test_offering_a_ride_notifies_the_driver(client, ride_data):
    response = offer(client, ride_data)
    assert response.status_code == 201, response.text
    ride = response.json()
    (n,) = inbox(client, auth(login(client)))
    assert n["type"] == "ride_created" and n["idRide"] == ride["id_ride"] and n["idBooking"] is None
    assert n["message"].startswith("Your Source → Destination ride on ")
    assert n["message"].endswith("is live with 3 seats available.")


# ===================== nothing is sent when the action fails =====================


def test_failed_actions_send_nothing(client, driver, rider, stranger):
    b = request_seats(client, rider, seats=2)
    before = (len(inbox(client, driver)), len(inbox(client, rider["headers"])), len(inbox(client, stranger["headers"])))
    assert approve(client, rider["headers"], b).status_code == 403  # not the driver
    assert approve(client, stranger["headers"], b).status_code == 404
    assert reject(client, rider["headers"], b).status_code == 403
    assert cancel(client, stranger["headers"], b).status_code == 404
    assert client.post("/v1/ride/booking", json={"id_ride": RIDE, "seats": 99}, headers=rider["headers"]).status_code == 422
    assert client.post("/v1/ride/booking", json={"id_ride": RIDE, "seats": 1}, headers=rider["headers"]).status_code == 409  # duplicate
    after = (len(inbox(client, driver)), len(inbox(client, rider["headers"])), len(inbox(client, stranger["headers"])))
    assert after == before


def test_repeated_actions_notify_once(client, driver, rider):
    b = request_seats(client, rider)
    assert approve(client, driver, b).status_code == 200
    assert approve(client, driver, b).status_code == 409
    assert cancel(client, rider["headers"], b).status_code == 200
    assert cancel(client, rider["headers"], b).status_code == 409
    assert types(client, rider["headers"]) == ["booking_accepted"]
    assert types(client, driver) == ["booking_cancelled", "booking_requested"]


def test_invalid_offer_sends_nothing(client, ride_data):
    ride_data["total_seats"] = 0
    assert offer(client, ride_data).status_code == 422
    assert inbox(client, auth(login(client))) == []


# ===================== atomicity: the notification and the change commit together =====================


@pytest.fixture
def broken_notifications(monkeypatch):
    def boom(self, params):
        raise RuntimeError("notification store is down")

    monkeypatch.setattr(NotificationRepository, "add", boom)


def test_booking_is_not_created_if_its_notification_cannot_be_saved(client, driver, rider, broken_notifications):
    with pytest.raises(RuntimeError):
        client.post("/v1/ride/booking", json={"id_ride": RIDE, "seats": 1}, headers=rider["headers"])
    with client.session() as db:
        assert db.execute(text("SELECT COUNT(*) FROM ride_booking")).scalar_one() == 0


def test_approval_rolls_back_with_its_notification(client, driver, rider, monkeypatch):
    b = request_seats(client, rider, seats=2)
    monkeypatch.setattr(NotificationRepository, "add", lambda self, params: (_ for _ in ()).throw(RuntimeError("down")))
    with pytest.raises(RuntimeError):
        approve(client, driver, b)
    assert booking_status(client, b) == "requested" and ride_row(client)[0] == 3  # seats not taken


def test_ride_is_not_created_if_its_notification_cannot_be_saved(client, ride_data, broken_notifications):
    with pytest.raises(RuntimeError):
        offer(client, ride_data)
    with client.session() as db:
        assert db.execute(text("SELECT COUNT(*) FROM ride")).scalar_one() == 0


# ===================== the notifications API shows them =====================


def test_notifications_can_be_marked_read(client, driver, rider):
    request_seats(client, rider)
    (n,) = inbox(client, driver)
    assert client.post(f"/v1/notifications/{n['idNotification']}/read", headers=driver).status_code in (200, 204)
    assert inbox(client, driver) == []


# ===================== reject endpoint =====================


def test_driver_rejects_a_request(client, driver, rider):
    b = request_seats(client, rider, seats=2)
    r = reject(client, driver, b, {"reason": "  full  "})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "rejected" and body["reject_reason"] == "full" and body["version"] == 2
    assert body["responded_at"].endswith("Z") and body["cancelled_at"] is None and body["cancel_reason"] is None
    assert ride_row(client)[:2] == (3, "open")  # a request never held seats


def test_reject_without_body_is_fine(client, driver, rider):
    b = request_seats(client, rider)
    r = reject(client, driver, b)
    assert r.status_code == 200 and r.json()["reject_reason"] is None


def test_rider_cannot_reject_403_and_strangers_get_404(client, driver, rider, stranger):
    b = request_seats(client, rider)
    assert reject(client, rider["headers"], b).status_code == 403
    assert reject(client, stranger["headers"], b).status_code == 404
    assert reject(client, driver, 123456789).status_code == 404
    assert client.post(f"/v1/ride/booking/{b}/reject").status_code == 401
    assert booking_status(client, b) == "requested"


@pytest.mark.parametrize("state", ["accepted", "rejected", "cancelled_by_rider", "cancelled_by_driver", "completed", "expired"])
def test_only_requested_bookings_can_be_rejected(client, driver, rider, state):
    b = request_seats(client, rider)
    with client.session() as db:
        db.execute(text("UPDATE ride_booking SET status = :s"), {"s": state})
        db.commit()
    r = reject(client, driver, b)
    assert r.status_code == 409 and state in r.json()["detail"]


@pytest.mark.parametrize("ride_status", ["started", "completed", "cancelled"])
def test_cannot_reject_once_the_ride_has_started(client, driver, rider, ride_status):
    b = request_seats(client, rider)
    with client.session() as db:
        db.execute(text("UPDATE ride SET status = :s"), {"s": ride_status})
        db.commit()
    assert reject(client, driver, b).status_code == 409 and booking_status(client, b) == "requested"


@pytest.mark.parametrize("body", [{"reason": "x" * 256}, {"reason": "ok", "status": "accepted"}, {"seats": 1}])
def test_invalid_reject_body_422(client, driver, rider, body):
    b = request_seats(client, rider)
    assert reject(client, driver, b, body).status_code == 422 and booking_status(client, b) == "requested"


def test_rider_can_request_again_after_a_rejection(client, driver, rider):
    b = request_seats(client, rider)
    reject(client, driver, b)
    assert request_seats(client, rider) != b


def test_a_rejected_booking_is_listed_as_past_for_the_rider(client, driver, rider):
    b = request_seats(client, rider)
    reject(client, driver, b)
    assert client.get("/v1/me/bookings", headers=rider["headers"]).json()["items"] == []
    past = client.get("/v1/me/bookings", headers=rider["headers"], params={"when": "past"}).json()["items"]
    assert [(i["id_booking"], i["status"]) for i in past] == [(b, "rejected")]
