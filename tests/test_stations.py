import pytest
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.main import app
from app.models import Station
from tests.test_auth_login import auth, client, login  # noqa: F401 (client fixture)
from tests.test_migrations_mysql import mysql_database  # noqa: F401 (opt-in fixture)

URL = "/v1/stations"


@pytest.fixture
def station_data(client):
    with client.session() as db:
        db.add_all([
            Station(id_station=20, station_name="Beta Terminal"),
            Station(id_station=10, station_name="Alpha Station"),
            Station(id_station=30, station_name="Closed Station", is_active=False),
            Station(id_station=40, station_name="100% Hub_One!"),
        ])
        db.commit()


def listing(client, params=None):
    return client.get(URL, params=params, headers=auth(login(client)))


def test_active_stations_sorted_and_serialized(client, station_data):
    response = listing(client)
    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["total"], body["limit"], body["offset"]) == (3, 100, 0)
    assert [row["station_name"] for row in body["items"]] == ["100% Hub_One!", "Alpha Station", "Beta Terminal"]
    assert all(row["is_active"] is True and row["created_at"].endswith("Z") for row in body["items"])
    assert all(isinstance(row["id_station"], int) for row in body["items"])


def test_include_inactive(client, station_data):
    body = listing(client, {"include_inactive": "true"}).json()
    assert body["total"] == 4
    assert next(row for row in body["items"] if row["id_station"] == 30)["is_active"] is False


@pytest.mark.parametrize("query, expected", [
    (" ALPHA ", [10]), ("terminal", [20]), ("%", [40]), ("_", [40]), ("!", [40]),
    ("' OR 1=1 --", []), ("does-not-exist", []), ("   ", [40, 10, 20]),
])
def test_literal_case_insensitive_search(client, station_data, query, expected):
    response = listing(client, {"search": query})
    assert response.status_code == 200
    body = response.json()
    assert [row["id_station"] for row in body["items"]] == expected
    assert body["total"] == len(expected)


def test_pagination_returns_filtered_total(client, station_data):
    body = listing(client, {"limit": 1, "offset": 1}).json()
    assert (body["total"], body["limit"], body["offset"]) == (3, 1, 1)
    assert [row["id_station"] for row in body["items"]] == [10]
    beyond = listing(client, {"offset": 100}).json()
    assert beyond["items"] == [] and beyond["total"] == 3


def test_search_and_active_filter_combine(client, station_data):
    assert listing(client, {"search": "Closed"}).json()["total"] == 0
    assert listing(client, {"search": "Closed", "include_inactive": "true"}).json()["total"] == 1


def test_empty_station_list(client):
    assert listing(client).json() == {"items": [], "total": 0, "limit": 100, "offset": 0}


@pytest.mark.parametrize("params", [
    {"limit": 0}, {"limit": 201}, {"offset": -1}, {"offset": "bad"},
    {"limit": 1.5}, {"include_inactive": "bad"}, {"search": "x" * 101},
])
def test_invalid_filters_422(client, params):
    assert listing(client, params).status_code == 422


@pytest.mark.parametrize("case, expected", [
    ("missing", "token_missing"), ("invalid", "token_invalid"), ("revoked", "session_revoked"),
])
def test_listing_requires_live_jwt(client, case, expected):
    token = login(client)
    headers = auth(token)
    if case == "missing":
        headers = {}
    elif case == "invalid":
        headers = {"Authorization": "Bearer invalid.token"}
    else:
        client.post("/v1/auth/logout", headers=headers)
    response = client.get(URL, headers=headers)
    assert response.status_code == 401
    assert response.json()["detail"]["code"] == expected
    assert response.headers["www-authenticate"] == "Bearer"


def test_swagger_has_filters_and_bearer_authorization():
    endpoint = app.openapi()["paths"][URL]["get"]
    assert endpoint["security"] == [{"AccessToken": []}]
    assert {param["name"] for param in endpoint["parameters"]} == {"search", "include_inactive", "limit", "offset"}


def test_station_listing_on_mysql(mysql_database):
    from alembic import command
    from fastapi.testclient import TestClient

    engine, config = mysql_database
    command.upgrade(config, "head")

    def override():
        with Session(engine) as db:
            yield db

    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override
    live = TestClient(app)
    try:
        user = {"email": "station-user@example.com", "phone": "+971503456789", "password": "Secret123"}
        assert live.post("/v1/auth/register", json=user).status_code == 201
        token = live.post("/v1/auth/login", json={"email": user["email"], "password": user["password"]}).json()
        with Session(engine) as db:
            db.add_all([
                Station(id_station=1, station_name="100% Station_One!"),
                Station(id_station=2, station_name="Hidden", is_active=False),
            ])
            db.commit()
        response = live.get(URL, params={"search": "%"}, headers=auth(token))
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["total"] == 1 and body["items"][0]["is_active"] is True
        assert body["items"][0]["created_at"].endswith("Z")
        body = live.get(URL, params={"include_inactive": "true", "limit": 1, "offset": 1}, headers=auth(token)).json()
        assert body["total"] == 2 and body["items"][0]["is_active"] is False
    finally:
        live.close()
        if previous is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous
