from datetime import date

import pytest
from sqlalchemy import text

from tests.test_auth_login import auth, client, login  # noqa: F401 (client is a fixture)
from tests.test_booking_actions import make_user
from tests.test_my_rides import OTHER, Data, hrs

URL = "/v1/users/{}/profile"
PRIVATE = {"phoneNumber", "phone", "email", "dateOfBirth", "phone_number"}


@pytest.fixture
def d(client):
    return Data(client)


@pytest.fixture
def me(client):
    return {"id": client.user_id, "headers": auth(login(client))}


@pytest.fixture
def stranger(client):
    return make_user(client, "stranger@example.com", "+971507777777")


def view(client, who, target):
    return client.get(URL.format(target), headers=who["headers"])


def set_profile(client, uid, **kw):
    cols = {"full_name": "Pat", **kw}
    with client.session() as db:
        db.execute(text("DELETE FROM user_profile WHERE id_user = :i"), {"i": uid})
        db.execute(
            text(f"INSERT INTO user_profile (id_user, {', '.join(cols)}) VALUES (:i, {', '.join(':' + k for k in cols)})"),
            {"i": uid, **cols},
        )
        db.commit()


def test_rider_can_see_driver_of_a_bookable_ride(client, d, me):
    d.ride(driver=OTHER, depart=hrs(5), status="open")
    r = view(client, me, OTHER)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["userId"] == str(OTHER) and body["fullName"] == "Other Driver"
    assert not PRIVATE & body.keys()


def test_driver_can_see_rider_who_booked_and_rider_sees_driver_after_ride_closes(client, d, me):
    ride = d.ride(driver=OTHER, depart=hrs(5), status="completed")  # no longer bookable
    d.booking(ride, rider=me["id"], status="completed")
    assert view(client, me, OTHER).status_code == 200  # rider → driver

    drv = make_user(client, "drv2@example.com", "+971509999999")
    ride2 = d.ride(driver=drv["id"], depart=hrs(6), status="started")
    d.booking(ride2, rider=me["id"], status="accepted")
    assert view(client, drv, me["id"]).status_code == 200


def test_strangers_get_404(client, d, me, stranger):
    d.ride(driver=OTHER, depart=hrs(5), status="cancelled")  # not bookable, no shared ride
    assert view(client, stranger, me["id"]).status_code == 404
    assert view(client, me, OTHER).status_code == 404
    assert view(client, me, 123456789).status_code == 404  # no such user


def test_you_can_see_yourself(client, me):
    assert view(client, me, me["id"]).status_code == 200


def test_fields_age_stats_and_vehicle(client, d, me):
    dob = date(date.today().year - 30, 1, 1)
    set_profile(client, OTHER, full_name="Arjun Mehta", about="Daily commute", gender="male",
                photo_url="http://x/a.png", date_of_birth=dob.isoformat())
    d.ride(driver=OTHER, depart=hrs(5), status="open")
    d.ride(driver=OTHER, depart=hrs(-30), status="completed")
    with client.session() as db:
        db.execute(text(
            "INSERT INTO vehicle (id_vehicle, id_user, make, model, color, registration_number, seat_capacity, "
            "vehicle_type, is_default, status) VALUES (77, :u, 'Maruti Suzuki', 'Swift', 'White', 'HR26AB1234', 4, 'car', 1, 'active')"
        ), {"u": OTHER})
        db.commit()
    body = view(client, me, OTHER).json()
    assert body["fullName"] == "Arjun Mehta" and body["about"] == "Daily commute" and body["gender"] == "male"
    assert body["age"] == 30 and body["photoUrl"] == "http://x/a.png"
    assert body["ridesDriven"] == 1 and body["ridesTaken"] == 0
    assert body["vehicle"] == {"make": "Maruti Suzuki", "model": "Swift", "color": "White", "vehicleType": "car"}
    assert "registrationNumber" not in str(body) and not PRIVATE & body.keys()


def test_user_without_profile_comes_back_with_nulls(client, d, me, stranger):
    d.ride(driver=stranger["id"], depart=hrs(5), status="open")
    body = view(client, me, stranger["id"]).json()
    assert body["fullName"] is None and body["about"] is None and body["age"] is None and body["vehicle"] is None


def test_requires_login(client):
    assert client.get(URL.format(OTHER)).status_code == 401
