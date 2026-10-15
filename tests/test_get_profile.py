from datetime import date

import pytest

from app.services.profile_service import age_on
from tests.test_auth_login import USER, auth, client, login  # noqa: F401 (client is a fixture)

URL = "/v1/auth/profile"


def save(client, user_id, **kw):
    r = client.post(URL, json={"userId": user_id, "fullName": "Jane Doe", **kw})
    assert r.status_code in (200, 201), r.text


def get(client, token=None):
    return client.get(URL, headers=auth(token or login(client)))


def test_returns_my_profile_with_age_and_contact_details(client):
    dob = date(date.today().year - 30, 1, 1)  # 30 for the whole year
    save(client, client.user_id, about="Commuter", photoUrl="http://x/y.png", dateOfBirth=dob.isoformat(), gender="female")
    r = get(client)
    assert r.status_code == 200, r.text
    assert r.json() == {
        "userId": str(client.user_id),
        "fullName": "Jane Doe",
        "photoUrl": "http://x/y.png",
        "about": "Commuter",
        "dateOfBirth": dob.isoformat(),
        "age": 30,
        "gender": "female",
        "email": USER["email"],
        "phoneNumber": USER["phone"],
    }


def test_optional_fields_come_back_null(client):
    save(client, client.user_id)
    body = get(client).json()
    assert body["dateOfBirth"] is None and body["age"] is None and body["gender"] is None
    assert body["photoUrl"] is None and body["about"] is None


def test_reflects_updates(client):
    save(client, client.user_id, about="first")
    save(client, client.user_id, fullName="Jane Smith", about="second")
    body = get(client).json()
    assert (body["fullName"], body["about"]) == ("Jane Smith", "second")


def test_404_until_a_profile_is_saved(client):
    r = get(client)
    assert r.status_code == 404 and r.json()["detail"] == "profile not found"


def test_each_user_only_sees_their_own_profile(client):
    save(client, client.user_id, about="mine")
    other = client.post("/v1/auth/register", json={"email": "o@example.com", "phone": "+971506666666", "password": "Secret123"}).json()
    token = client.post("/v1/auth/login", json={"email": "o@example.com", "password": "Secret123"}).json()
    assert get(client, token).status_code == 404  # the other user has no profile; mine is not leaked
    save(client, int(other["userId"]), fullName="Other Person", about="theirs")
    assert get(client, token).json()["about"] == "theirs"
    assert get(client).json()["about"] == "mine"


def test_requires_login(client):
    save(client, client.user_id)
    assert client.get(URL).status_code == 401
    assert client.get(URL, headers={"Authorization": "Bearer nonsense"}).status_code == 401


def test_logged_out_session_is_rejected(client):
    save(client, client.user_id)
    token = login(client)
    assert client.post("/v1/auth/logout", headers=auth(token), json={"refreshToken": token["refreshToken"]}).status_code in (200, 204)
    assert get(client, token).status_code == 401


@pytest.mark.parametrize(
    "dob, today, expected",
    [
        (date(1995, 4, 12), date(2026, 4, 11), 30),  # birthday is tomorrow
        (date(1995, 4, 12), date(2026, 4, 12), 31),  # birthday today
        (date(1995, 4, 12), date(2026, 12, 31), 31),
        (date(2000, 2, 29), date(2026, 2, 28), 25),  # leap-day birthday, not yet reached
        (date(2000, 2, 29), date(2026, 3, 1), 26),
        (date(2026, 1, 1), date(2026, 1, 1), 0),
        (None, date(2026, 1, 1), None),
    ],
)
def test_age_on(dob, today, expected):
    assert age_on(dob, today) == expected
