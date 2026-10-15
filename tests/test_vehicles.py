import pytest
from sqlalchemy import text

from tests.test_auth_login import USER, auth, client, login  # noqa: F401  (client is a fixture)

URL = "/v1/vehicles"
CAR = {
    "make": " Toyota ", "model": "Corolla", "color": "White",
    "registrationNumber": "ka 01 ab 1234", "seatCapacity": 4, "vehicleType": "sedan",
}


@pytest.fixture
def h(client):
    return auth(login(client))


def other_user_headers(client):
    other = {"email": "other@example.com", "phone": "+971504444444", "password": "Secret123"}
    client.post("/v1/auth/register", json=other)
    return auth(client.post("/v1/auth/login", json={"email": other["email"], "password": other["password"]}).json())


def add(client, h, **kw):
    r = client.post(URL, json={**CAR, **kw}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def test_create_normalizes_and_first_is_default(client, h):
    v = add(client, h)
    assert v["make"] == "Toyota" and v["registrationNumber"] == "KA01AB1234"
    assert v["isDefault"] is True and v["status"] == "active"
    assert v["createdAt"].endswith("Z") and isinstance(v["vehicleId"], str)
    with client.session() as db:
        owner = db.execute(text("SELECT id_user FROM vehicle WHERE id_vehicle = :i"), {"i": int(v["vehicleId"])}).scalar()
    assert owner == client.user_id


def test_second_vehicle_not_default_unless_asked(client, h):
    first = add(client, h)
    second = add(client, h, registrationNumber="B2")
    assert second["isDefault"] is False
    third = add(client, h, registrationNumber="C3", isDefault=True)
    assert third["isDefault"] is True
    by_id = {v["vehicleId"]: v for v in client.get(URL, headers=h).json()}
    assert [by_id[x["vehicleId"]]["isDefault"] for x in (first, second, third)] == [False, False, True]


def test_list_default_first_and_status_filter(client, h):
    a = add(client, h)
    b = add(client, h, registrationNumber="B2")
    client.patch(f"{URL}/{b['vehicleId']}", json={"status": "inactive"}, headers=h)
    assert [v["vehicleId"] for v in client.get(URL, headers=h).json()] == [a["vehicleId"], b["vehicleId"]]
    assert [v["vehicleId"] for v in client.get(URL, params={"status": "inactive"}, headers=h).json()] == [b["vehicleId"]]
    assert client.get(URL, params={"status": "deleted"}, headers=h).status_code == 422


def test_get_one(client, h):
    v = add(client, h)
    assert client.get(f"{URL}/{v['vehicleId']}", headers=h).json() == v
    assert client.get(f"{URL}/123", headers=h).status_code == 404


def test_patch_partial_update(client, h):
    v = add(client, h)
    r = client.patch(f"{URL}/{v['vehicleId']}", json={"color": " Red ", "seatCapacity": 5}, headers=h)
    assert r.status_code == 200
    body = r.json()
    assert (body["color"], body["seatCapacity"], body["make"]) == ("Red", 5, "Toyota")


def test_patch_default_moves(client, h):
    a = add(client, h)
    b = add(client, h, registrationNumber="B2")
    assert client.patch(f"{URL}/{b['vehicleId']}", json={"isDefault": True}, headers=h).json()["isDefault"] is True
    assert client.get(f"{URL}/{a['vehicleId']}", headers=h).json()["isDefault"] is False


def test_deactivating_default_clears_it_and_inactive_cannot_be_default(client, h):
    v = add(client, h)
    r = client.patch(f"{URL}/{v['vehicleId']}", json={"status": "inactive"}, headers=h)
    assert (r.json()["status"], r.json()["isDefault"]) == ("inactive", False)
    r = client.patch(f"{URL}/{v['vehicleId']}", json={"isDefault": True}, headers=h)
    assert r.status_code == 409
    assert client.patch(f"{URL}/{v['vehicleId']}", json={"status": "active", "isDefault": True}, headers=h).status_code == 200


def test_duplicate_registration_409(client, h):
    add(client, h)
    assert client.post(URL, json={**CAR, "registrationNumber": "KA01 AB1234"}, headers=h).status_code == 409
    b = add(client, h, registrationNumber="B2")
    r = client.patch(f"{URL}/{b['vehicleId']}", json={"registrationNumber": "ka01ab1234"}, headers=h)
    assert r.status_code == 409
    # another user can't take it either
    assert client.post(URL, json=CAR, headers=other_user_headers(client)).status_code == 409


def test_delete_is_soft_and_frees_registration(client, h):
    v = add(client, h)
    assert client.delete(f"{URL}/{v['vehicleId']}", headers=h).status_code == 204
    assert client.get(f"{URL}/{v['vehicleId']}", headers=h).status_code == 404
    assert client.get(URL, headers=h).json() == []
    assert client.delete(f"{URL}/{v['vehicleId']}", headers=h).status_code == 404
    assert client.patch(f"{URL}/{v['vehicleId']}", json={"color": "Red"}, headers=h).status_code == 404
    again = add(client, h)  # same registration number, now free
    assert again["vehicleId"] != v["vehicleId"] and again["isDefault"] is True


def test_cannot_touch_other_users_vehicle(client, h):
    v = add(client, h)
    theirs = other_user_headers(client)
    for method in ("get", "patch", "delete"):
        kwargs = {"json": {"color": "Red"}} if method == "patch" else {}
        r = getattr(client, method)(f"{URL}/{v['vehicleId']}", headers=theirs, **kwargs)
        assert r.status_code == 404, method
    assert client.get(URL, headers=theirs).json() == []
    assert client.get(f"{URL}/{v['vehicleId']}", headers=h).json()["color"] == "White"


@pytest.mark.parametrize(
    "patch",
    [
        {"seatCapacity": 0}, {"seatCapacity": 9}, {"vehicleType": "truck"}, {"make": "  "},
        {"registrationNumber": "AB#12"}, {"make": "x" * 51},
    ],
)
def test_create_validation_422(client, h, patch):
    assert client.post(URL, json={**CAR, **patch}, headers=h).status_code == 422


@pytest.mark.parametrize("body", [{}, {"color": None}, {"status": "deleted"}, {"seatCapacity": 12}])
def test_patch_validation_422(client, h, body):
    v = add(client, h)
    assert client.patch(f"{URL}/{v['vehicleId']}", json=body, headers=h).status_code == 422


@pytest.mark.parametrize(
    "method, path", [("post", URL), ("get", URL), ("get", f"{URL}/1"), ("patch", f"{URL}/1"), ("delete", f"{URL}/1")]
)
def test_all_routes_need_session(client, method, path):
    kwargs = {"json": CAR} if method in ("post", "patch") else {}
    r = getattr(client, method)(path, **kwargs)
    assert r.status_code == 401 and r.json()["detail"]["code"] == "token_missing"
