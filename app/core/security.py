import base64
import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import settings

# scrypt from the stdlib: no extra dependency. Swap for argon2/bcrypt if preferred.
_N, _R, _P = 2**14, 8, 1


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P)
    return "scrypt${}${}".format(
        base64.b64encode(salt).decode(), base64.b64encode(digest).decode()
    )


def verify_password(password: str, stored: str) -> bool:
    try:
        _, salt_b64, digest_b64 = stored.split("$")
    except ValueError:
        return False
    salt, expected = base64.b64decode(salt_b64), base64.b64decode(digest_b64)
    actual = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P)
    return hmac.compare_digest(actual, expected)


# Verified against when no user matches, so unknown accounts take as long as wrong passwords.
_DUMMY_HASH = hash_password(os.urandom(16).hex())


def verify_password_or_dummy(password: str, stored: str | None) -> bool:
    ok = verify_password(password, stored or _DUMMY_HASH)
    return stored is not None and ok


def create_access_token(user_id: int) -> tuple[str, int]:
    """Return (HS256 JWT, lifetime in seconds)."""
    expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    now = datetime.now(timezone.utc)
    claims = {"sub": str(user_id), "iat": now, "exp": now + timedelta(seconds=expires_in)}
    return jwt.encode(claims, settings.JWT_SECRET, algorithm="HS256"), expires_in


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
