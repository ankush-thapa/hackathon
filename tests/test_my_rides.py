from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from tests.test_auth_login import auth, client, login  # noqa: F401 (client is a fixture)

URLS = {"driver": "/v1/me/rides", "rider": "/v1/me/bookings"}
OTHER = 999  # some other user: driver of rides the caller books, rider on the caller's rides


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def hrs(h):
    return now() + timedelta(hours=h)


class Data:
    """Raw-SQL fixture builder; ids are handed out sequentially."""

    def __init__(self, client):
        self.c = client
        self.n = 0
        with client.session() as db:
            for sid, name in ((1, "Alpha"), (2, "Beta")):
                db.execute(text("INSERT INTO station (id_station, station_name) VALUES (:i, :n)"), {"i": sid, "n": name})
            db.execute(text("INSERT INTO `user` (id_user, email, password_hash) VALUES (:i, 'o@x.co', 'h')"), {"i": OTHER})
            db.execute(text("INSERT INTO user_profile (id_user, full_name) VALUES (:i, 'Other Driver')"), {"i": OTHER})
            db.commit()

    def ride(self, *, driver, depart, status="open", seats=3):
        self.n += 1
        with self.c.session() as db:
            db.execute(
                text(
                    "INSERT INTO ride (id_ride, id_driver, id_vehicle, id_source_station, id_destination_station, "
                    "departure_time, total_seats, available_seats, price_per_seat, status, version) "
                    "VALUES (:i, :d, 1, 1, 2, :t, 4, :s, 20.00, :st, 1)"
                ),
                {"i": self.n, "d": driver, "t": depart, "s": seats, "st": status},
            )
            db.commit()
        return str(self.n)

    def booking(self, ride, *, rider, seats=1, status="requested"):
        self.n += 1
        with self.c.session() as db:
            db.execute(
                text(
                    "INSERT INTO ride_booking (id_booking, id_ride, id_rider, id_driver, seats_booked, price_per_seat, "
                    "total_amount, rider_note, status, version) "
                    "VALUES (:b, :r, :u, 0, :s, 20.00, :a, 'note', :st, 1)"
                ),
                {"b": 5000 + self.n, "r": int(ride), "u": rider, "s": seats, "a": 20 * seats, "st": status},
            )
            db.commit()
        return str(5000 + self.n)


@pytest.fixture
def d(client):
    return Data(client)


def get(client, who, **params):
    return client.get(URLS[who], params=params, headers=auth(login(client)))


def ride_ids(r):
    """Ride id of each row (driver rows are rides; rider rows are bookings with the ride nested)."""
    return [i["ride"]["id_ride"] if "ride" in i else i["id_ride"] for i in r.json()["items"]]


def booking_ids(r):
    return [i["id_booking"] for i in r.json()["items"]]


# ---------- driver ----------


def test_driver_lists_only_own_rides_with_request_counts(client, d):
    me = client.user_id
    mine = d.ride(driver=me, depart=hrs(5), seats=1)
    d.ride(driver=OTHER, depart=hrs(6))  # someone else's ride
    d.booking(mine, rider=OTHER, seats=1, status="requested")
    d.booking(mine, rider=777, seats=2, status="requested")
    d.booking(mine, rider=778, seats=2, status="accepted")
    d.booking(mine, rider=779, seats=1, status="rejected")
    r = get(client, "driver")
    assert r.status_code == 200, r.text
    assert ride_ids(r) == [mine]
    item = r.json()["items"][0]
    assert item["requests"] == {"pending_requests": 2, "accepted_seats": 2}
    assert "booking" not in item
    assert item["source"] == {"id_station": 1, "name": "Alpha"}
    assert item["driver"]["id_user"] == str(me) and item["status"] == "open"
    assert item["price_per_seat"] == "20.00" and item["available_seats"] == 1


def test_driver_upcoming_vs_past(client, d):
    me = client.user_id
    soon = d.ride(driver=me, depart=hrs(2))
    later = d.ride(driver=me, depart=hrs(30), status="full", seats=0)
    started = d.ride(driver=me, depart=hrs(-1), status="started")  # in progress counts as upcoming
    cancelled = d.ride(driver=me, depart=hrs(10), status="cancelled")
    done = d.ride(driver=me, depart=hrs(-48), status="completed")
    stale = d.ride(driver=me, depart=hrs(-5))  # open but never started, departure passed
    assert ride_ids(get(client, "driver")) == [started, soon, later]  # default = upcoming, soonest first
    assert ride_ids(get(client, "driver", when="upcoming")) == [started, soon, later]
    past = ride_ids(get(client, "driver", when="past"))
    assert set(past) == {cancelled, done, stale}
    assert past == [cancelled, stale, done]  # most recent departure first
    assert set(ride_ids(get(client, "driver", when="all"))) == {soon, later, started, cancelled, done, stale}


# ---------- rider ----------


def test_rider_lists_own_bookings_with_ride_and_booking_details(client, d):
    me = client.user_id
    ride = d.ride(driver=OTHER, depart=hrs(4))
    other_ride = d.ride(driver=OTHER, depart=hrs(5))
    b = d.booking(ride, rider=me, seats=2, status="accepted")
    d.booking(other_ride, rider=777)  # someone else's booking
    r = get(client, "rider")
    assert r.status_code == 200, r.text
    assert ride_ids(r) == [ride]
    item = r.json()["items"][0]
    assert {k: item[k] for k in ("id_booking", "seats_booked", "price_per_seat", "total_amount", "status", "rider_note")} == {
        "id_booking": b, "seats_booked": 2, "price_per_seat": "20.00", "total_amount": "40.00",
        "status": "accepted", "rider_note": "note",
    }
    assert item["created_at"].endswith("Z")
    assert "requests" not in item
    ride_info = item["ride"]
    assert ride_info["id_ride"] == ride and ride_info["status"] == "open"
    assert ride_info["driver"] == {"id_user": str(OTHER), "full_name": "Other Driver", "photo_url": None}
    assert ride_info["destination"] == {"id_station": 2, "name": "Beta"}


def test_rider_upcoming_vs_past(client, d):
    me = client.user_id
    active = d.booking(d.ride(driver=OTHER, depart=hrs(3)), rider=me, status="requested")
    accepted = d.booking(d.ride(driver=OTHER, depart=hrs(8)), rider=me, status="accepted")
    cancelled = d.booking(d.ride(driver=OTHER, depart=hrs(9)), rider=me, status="cancelled_by_rider")
    rejected = d.booking(d.ride(driver=OTHER, depart=hrs(10)), rider=me, status="rejected")
    done = d.booking(d.ride(driver=OTHER, depart=hrs(-30), status="completed"), rider=me, status="completed")
    left = d.booking(d.ride(driver=OTHER, depart=hrs(-2)), rider=me, status="accepted")  # departed, never started

    def ids(**p):
        return booking_ids(get(client, "rider", **p))

    assert ids() == [active, accepted]  # upcoming = still-active bookings on rides ahead
    assert set(ids(when="past")) == {cancelled, rejected, done, left}
    assert ids(when="past") == [rejected, cancelled, left, done]  # most recent departure first
    assert len(ids(when="all")) == 6


def test_rebooking_after_cancel_gives_one_row_per_booking(client, d):
    ride = d.ride(driver=OTHER, depart=hrs(6))
    first = d.booking(ride, rider=client.user_id, status="cancelled_by_rider")
    second = d.booking(ride, rider=client.user_id, status="requested")
    assert sorted(booking_ids(get(client, "rider", when="all"))) == sorted([first, second])
    assert booking_ids(get(client, "rider")) == [second]


def test_same_user_is_driver_and_rider_separately(client, d):
    me = client.user_id
    offered = d.ride(driver=me, depart=hrs(2))
    booked = d.ride(driver=OTHER, depart=hrs(3))
    d.booking(booked, rider=me)
    assert ride_ids(get(client, "driver")) == [offered]
    assert ride_ids(get(client, "rider")) == [booked]


def test_empty(client, d):
    for role in ("driver", "rider"):
        assert get(client, role).json() == {"items": [], "next_page": None, "prev_page": None}


# ---------- pagination ----------


@pytest.mark.parametrize("role, when", [("driver", "upcoming"), ("driver", "past"), ("rider", "upcoming"), ("rider", "past")])
def test_pagination_forward_and_back(client, d, role, when):
    me = client.user_id
    sign = 1 if when == "upcoming" else -1
    t0 = now()  # one shared base so equal offsets give identical departure times

    def at(h):
        return t0 + timedelta(hours=sign * h)

    for i in range(5):
        depart = at(2 + i)
        if role == "driver":
            d.ride(driver=me, depart=depart, status="open" if when == "upcoming" else "completed")
        else:
            ride = d.ride(driver=OTHER, depart=depart, status="open" if when == "upcoming" else "completed")
            d.booking(ride, rider=me, status="accepted" if when == "upcoming" else "completed")
    if role == "driver":  # same departure time as the first ride: the tie is broken by id
        d.ride(driver=me, depart=at(2), status="open" if when == "upcoming" else "completed")

    def key(i):
        return i["id_booking"] if role == "rider" else i["id_ride"]

    everything = [key(i) for i in get(client, role, when=when).json()["items"]]
    assert len(everything) == (6 if role == "driver" else 5)

    def page(cursor=None):
        p = {"when": when, "page_size": 2} | ({"cursor": cursor} if cursor else {})
        body = get(client, role, **p).json()
        return [key(i) for i in body["items"]], body["next_page"], body["prev_page"]

    p1, n1, pv1 = page()
    assert p1 == everything[:2] and n1 and pv1 is None
    p2, n2, pv2 = page(n1)
    assert p2 == everything[2:4] and n2 and pv2
    p3, n3, pv3 = page(n2)
    assert p3 == everything[4:] and n3 is None and pv3
    b2, nb2, pvb2 = page(pv3)
    assert b2 == p2 and nb2 and pvb2
    b1, nb1, pvb1 = page(pvb2)
    assert b1 == p1 and nb1 and pvb1 is None


# ---------- validation / auth ----------


@pytest.mark.parametrize("role", ["driver", "rider"])
def test_requires_login(client, d, role):
    assert client.get(URLS[role]).status_code == 401


@pytest.mark.parametrize("role", ["driver", "rider"])
@pytest.mark.parametrize(
    "params",
    [
        {"when": "yesterday"},
        {"page_size": 0},
        {"page_size": 51},
        {"cursor": "garbage"},
    ],
)
def test_validation_422(client, d, role, params):
    assert get(client, role, **params).status_code == 422


def test_old_role_parameter_is_gone_and_ignored(client, d):
    ride = d.ride(driver=client.user_id, depart=hrs(3))
    # `role` no longer exists: /v1/me/rides is always the driver view
    assert ride_ids(get(client, "driver", role="rider")) == [ride]
