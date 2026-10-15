from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user_id
from app.db.session import Base, get_db
from app.main import app

URL = "/v1/rides"
SRC, DST, OTHER = 1, 2, 3
DRIVER = 1001


def now_utc():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def today():
    return datetime.now(timezone.utc).date()


def day(n):
    """ISO date n days from today (UTC)."""
    return (today() + timedelta(days=n)).isoformat()


def at(n, hour=12):
    """Naive-UTC datetime at `hour` o'clock on the day n days from today."""
    return datetime.combine(today() + timedelta(days=n), datetime.min.time()) + timedelta(hours=hour)


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

    with Session() as db:
        for i, name in ((SRC, "Alpha"), (DST, "Beta"), (OTHER, "Gamma")):
            db.execute(text("INSERT INTO station (id_station, station_name, is_active) VALUES (:i, :n, 1)"), {"i": i, "n": name})
        db.execute(text("INSERT INTO station (id_station, station_name, is_active) VALUES (9, 'Closed', 0)"))
        db.execute(text("INSERT INTO `user` (id_user, email, password_hash) VALUES (:d, 'd@x.co', 'h')"), {"d": DRIVER})
        db.execute(text("INSERT INTO user_profile (id_user, full_name) VALUES (:d, 'Dina Driver')"), {"d": DRIVER})
        db.commit()

    prev_db = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override
    app.dependency_overrides[get_current_user_id] = lambda: 42
    c = TestClient(app)
    c.session = Session
    c.next_id = 1
    yield c
    app.dependency_overrides.pop(get_current_user_id, None)
    if prev_db is None:
        app.dependency_overrides.pop(get_db, None)
    else:
        app.dependency_overrides[get_db] = prev_db


def add_ride(client, *, src=SRC, dst=DST, depart=None, seats=3, total=4, status="open", price="25.50", vehicle=None, driver=DRIVER):
    rid = client.next_id
    client.next_id += 1
    with client.session() as db:
        db.execute(
            text(
                "INSERT INTO ride (id_ride, id_driver, id_vehicle, id_source_station, id_destination_station, "
                "departure_time, total_seats, available_seats, price_per_seat, status, version) "
                "VALUES (:id, :drv, :veh, :s, :d, :t, :total, :seats, :price, :status, 1)"
            ),
            {"id": rid, "drv": driver, "veh": vehicle or 7, "s": src, "d": dst, "t": depart or at(1), "total": total,
             "seats": seats, "price": price, "status": status},
        )
        db.commit()
    return str(rid)


def params(**kw):
    base = {"idSourceStation": SRC, "idDestinationStation": DST, "departureDate": day(1)}
    return {**base, **kw}


def ids(r):
    return [i["idRide"] for i in r.json()["items"]]


def test_requires_session():
    app.dependency_overrides.pop(get_current_user_id, None)
    r = TestClient(app).get(URL, params=params())
    assert r.status_code == 401


def test_filters_by_stations_and_returns_details(client):
    match = add_ride(client)
    add_ride(client, src=DST, dst=SRC)  # reverse direction
    add_ride(client, dst=OTHER)  # other destination
    r = client.get(URL, params=params())
    assert r.status_code == 200 and ids(r) == [match]
    item = r.json()["items"][0]
    assert item["source"] == {"idStation": SRC, "name": "Alpha"}
    assert item["destination"] == {"idStation": DST, "name": "Beta"}
    assert item["driver"] == {"userId": str(DRIVER), "fullName": "Dina Driver", "photoUrl": None}
    assert item["availableSeats"] == 3 and item["totalSeats"] == 4 and item["pricePerSeat"] == "25.50"
    assert item["vehicle"] is None  # no vehicle row: still listed
    assert r.json()["next_page"] is None and r.json()["prev_page"] is None


def test_own_rides_are_not_listed(client):
    with client.session() as db:
        db.execute(text("INSERT INTO `user` (id_user, email, password_hash) VALUES (2002, 'e@x.co', 'h')"))
        db.commit()
    mine = add_ride(client, depart=at(1, 2))  # offered by DRIVER (1001)
    theirs = add_ride(client, depart=at(1, 3), driver=2002)
    # the caller is a rider (42): sees both
    assert ids(client.get(URL, params=params())) == [mine, theirs]
    # the caller is the driver of `mine`: it disappears from their search, the other driver's ride stays
    app.dependency_overrides[get_current_user_id] = lambda: DRIVER
    r = client.get(URL, params=params())
    assert ids(r) == [theirs]
    # ...and the exclusion does not break paging
    page = client.get(URL, params=params(pageSize=1)).json()
    assert [i["idRide"] for i in page["items"]] == [theirs] and page["next_page"] is None


def test_filters_by_available_seats(client):
    one = add_ride(client, seats=1, depart=at(1, 2))
    three = add_ride(client, seats=3, depart=at(1, 3))
    add_ride(client, seats=0, status="full", depart=at(1, 4))
    assert ids(client.get(URL, params=params())) == [one, three]  # default seats=1
    assert ids(client.get(URL, params=params(seats=2))) == [three]
    assert ids(client.get(URL, params=params(seats=4))) == []


def test_filters_by_departure_date(client):
    tomorrow_first = add_ride(client, depart=at(1, 0))  # first instant of the day: included
    tomorrow_last = add_ride(client, depart=at(1, 23) + timedelta(minutes=59))  # last minute: included
    add_ride(client, depart=at(0, 23) + timedelta(minutes=59))  # the day before: excluded
    day_after_first = add_ride(client, depart=at(2, 0))  # first instant of the next day: only on that date
    add_ride(client, depart=at(3, 10))
    assert ids(client.get(URL, params=params(departureDate=day(1)))) == [tomorrow_first, tomorrow_last]
    assert ids(client.get(URL, params=params(departureDate=day(2)))) == [day_after_first]
    assert ids(client.get(URL, params=params(departureDate=day(5)))) == []


def test_never_lists_rides_that_already_left(client):
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    add_ride(client, depart=now - timedelta(hours=1))
    add_ride(client, depart=now - timedelta(minutes=1))
    assert ids(client.get(URL, params=params(departureDate=today().isoformat()))) == []


@pytest.mark.parametrize("days_ago", [1, 2, 365])
def test_past_dates_are_rejected(client, days_ago):
    add_ride(client, depart=at(-days_ago, 12))  # even if a ride exists on that date
    r = client.get(URL, params=params(departureDate=day(-days_ago)))
    assert r.status_code == 422 and r.json()["detail"] == "departureDate must not be in the past"


def test_today_is_allowed(client):
    r = client.get(URL, params=params(departureDate=today().isoformat()))
    assert r.status_code == 200 and r.json()["items"] == []  # nothing offered, but today itself is a valid date


def test_only_open_rides(client):
    add_ride(client, status="cancelled", depart=at(1, 1))
    add_ride(client, status="started", depart=at(1, 3))
    add_ride(client, status="completed", depart=at(1, 4))
    open_ride = add_ride(client, depart=at(1, 5))
    assert ids(client.get(URL, params=params())) == [open_ride]


def test_sorted_by_departure_time(client):
    b = add_ride(client, depart=at(1, 6))
    a = add_ride(client, depart=at(1, 2))
    c = add_ride(client, depart=at(1, 9))
    assert ids(client.get(URL, params=params())) == [a, b, c]


def test_pagination_forward_and_back(client):
    for i in range(5):
        add_ride(client, depart=at(1, 2 + i))
    add_ride(client, depart=at(1, 2))  # same departure as the first: tie broken by id
    everything = ids(client.get(URL, params=params()))
    assert len(everything) == 6

    def page(cursor=None):
        body = client.get(URL, params=params(pageSize=2) | ({"cursor": cursor} if cursor else {})).json()
        return [i["idRide"] for i in body["items"]], body["next_page"], body["prev_page"]

    p1, next1, prev1 = page()
    assert p1 == everything[:2] and next1 and prev1 is None  # first page has no prev
    p2, next2, prev2 = page(next1)
    assert p2 == everything[2:4] and next2 and prev2
    p3, next3, prev3 = page(next2)
    assert p3 == everything[4:] and next3 is None and prev3  # last page has no next
    # and back again
    back2, next_b2, prev_b2 = page(prev3)
    assert back2 == p2 and next_b2 and prev_b2
    back1, next_b1, prev_b1 = page(prev_b2)
    assert back1 == p1 and next_b1 and prev_b1 is None  # reached the start


def test_prev_page_when_fewer_than_page_size_remain_before(client):
    for i in range(3):
        add_ride(client, depart=at(1, 2 + i))
    everything = ids(client.get(URL, params=params()))
    body = client.get(URL, params=params(pageSize=2)).json()
    last = client.get(URL, params=params(pageSize=2, cursor=body["next_page"])).json()
    assert [i["idRide"] for i in last["items"]] == everything[2:]
    back = client.get(URL, params=params(pageSize=5, cursor=last["prev_page"])).json()
    assert [i["idRide"] for i in back["items"]] == everything[:2]
    assert back["prev_page"] is None and back["next_page"]


@pytest.mark.parametrize(
    "patch, code",
    [
        ({"idDestinationStation": SRC}, 422),
        ({"idSourceStation": 0}, 422),
        ({"seats": 0}, 422),
        ({"seats": 9}, 422),
        ({"pageSize": 0}, 422),
        ({"pageSize": 51}, 422),
        ({"departureDate": "not-a-date"}, 422),
        ({"departureDate": "2026-13-45"}, 422),
        ({"cursor": "garbage"}, 422),
        ({"idSourceStation": 777}, 404),
        ({"idDestinationStation": 9}, 404),  # inactive station
    ],
)
def test_validation(client, patch, code):
    assert client.get(URL, params=params(**patch)).status_code == code


def test_departure_date_is_required(client):
    p = params()
    del p["departureDate"]
    assert client.get(URL, params=p).status_code == 422
    assert client.get(URL, params={"idSourceStation": SRC}).status_code == 422
