import uuid
from pathlib import Path
from typing import BinaryIO

# Detected from file contents (magic bytes), never from the client-supplied Content-Type or filename.
_CHUNK = 64 * 1024


class UnsupportedMediaError(Exception):
    pass


class FileTooLargeError(Exception):
    pass


def _detect_image(head: bytes) -> tuple[str, str] | None:
    """Returns (extension, content_type) or None."""
    if head.startswith(b"\xff\xd8\xff"):
        return "jpg", "image/jpeg"
    if head.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png", "image/png"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "webp", "image/webp"
    return None


class MediaService:
    def __init__(self, media_dir: Path, max_bytes: int):
        self._dir = media_dir
        self._max = max_bytes

    def save_image(self, src: BinaryIO) -> dict:
        """Validates and stores an image under a random name. Raises UnsupportedMediaError / FileTooLargeError."""
        head = src.read(12)
        detected = _detect_image(head)
        if detected is None:
            raise UnsupportedMediaError
        ext, content_type = detected

        self._dir.mkdir(parents=True, exist_ok=True)
        name = f"{uuid.uuid4().hex}.{ext}"  # server-generated: no path traversal, no collisions
        dest = self._dir / name
        size = len(head)
        try:
            with open(dest, "xb") as out:
                out.write(head)
                while chunk := src.read(_CHUNK):
                    size += len(chunk)
                    if size > self._max:
                        raise FileTooLargeError
                    out.write(chunk)
        except BaseException:
            dest.unlink(missing_ok=True)  # never leave a partial file behind
            raise
        return {"fileName": name, "contentType": content_type, "size": size}
