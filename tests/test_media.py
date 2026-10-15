import pytest
from fastapi.testclient import TestClient

from app.api.media import get_media_service
from app.main import app
from app.services.media_service import MediaService

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
WEBP = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 64
URL = "/v1/media/upload"


@pytest.fixture
def client(tmp_path):
    app.dependency_overrides[get_media_service] = lambda: MediaService(tmp_path, max_bytes=1024)
    c = TestClient(app)
    c.dir = tmp_path
    yield c
    app.dependency_overrides.pop(get_media_service, None)


@pytest.mark.parametrize("data, ext, ctype", [(PNG, "png", "image/png"), (JPG, "jpg", "image/jpeg"), (WEBP, "webp", "image/webp")])
def test_upload_stores_file_and_returns_url(client, data, ext, ctype):
    r = client.post(URL, files={"file": ("my photo.exe", data, "application/octet-stream")})
    assert r.status_code == 201
    body = r.json()
    assert body["contentType"] == ctype and body["size"] == len(data)
    assert body["fileName"].endswith(f".{ext}") and "my" not in body["fileName"]  # client filename ignored
    assert body["url"] == f"http://testserver/media/{body['fileName']}"
    assert (client.dir / body["fileName"]).read_bytes() == data


def test_non_image_rejected_even_with_image_content_type(client):
    r = client.post(URL, files={"file": ("a.png", b"<html>not an image</html>", "image/png")})
    assert r.status_code == 415
    assert list(client.dir.iterdir()) == []


def test_too_large_rejected_and_cleaned_up(client):
    r = client.post(URL, files={"file": ("a.png", PNG + b"\x00" * 2000, "image/png")})
    assert r.status_code == 413
    assert list(client.dir.iterdir()) == []


def test_missing_file_422(client):
    assert client.post(URL).status_code == 422


def test_each_upload_gets_unique_name(client):
    names = {client.post(URL, files={"file": ("a.png", PNG, "image/png")}).json()["fileName"] for _ in range(3)}
    assert len(names) == 3
