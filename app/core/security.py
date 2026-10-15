import base64
import hashlib
import hmac
import os
import secrets
from datetime import datetime

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


def create_access_token(user_id: int, session_id: int, issued_at: datetime, expires_at: datetime) -> str:
    """HS256 JWT. `sid` ties the token to a user_session row so it can be revoked early."""
    claims = {"sub": str(user_id), "sid": str(session_id), "iat": issued_at, "exp": expires_at}
    return jwt.encode(claims, settings.JWT_SECRET, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    """Raises jwt.InvalidTokenError (incl. ExpiredSignatureError) on a bad or expired token."""
    return jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"], options={"require": ["exp", "sub", "sid"]})


def new_refresh_token(session_id: int) -> tuple[str, str]:
    """Return (token for the client, sha256 hex to store). The session id prefix makes lookup a primary-key read."""
    secret = secrets.token_urlsafe(32)
    return f"{session_id}.{secret}", hash_refresh_secret(secret)


def parse_refresh_token(token: str) -> tuple[int, str] | None:
    """Split a refresh token into (session id, secret hash), or None if it is malformed."""
    session_part, _, secret = token.partition(".")
    if not session_part.isdigit() or not secret:
        return None
    return int(session_part), hash_refresh_secret(secret)


def hash_refresh_secret(secret: str) -> str:
    # The secret is 256 random bits, so a fast hash is enough; it only keeps DB readers from using it.
    return hashlib.sha256(secret.encode()).hexdigest()
