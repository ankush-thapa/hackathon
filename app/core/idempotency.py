import hashlib
import hmac

from fastapi import HTTPException
from app.core.config import settings
from app.core.ids import new_id


def creation_id(user_id: int, operation: str, key: str | None) -> int:
    """Optional retry key maps to an existing model's primary key; no new tables.

    Keys are scoped by caller and operation. Retain the same JWT_SECRET across replicas.
    A replay returns current resource state, not a historical response snapshot.
    """
    if key is None:
        return new_id()
    if not 8 <= len(key) <= 128 or not key.strip():
        raise HTTPException(422, "Idempotency-Key must contain 8-128 characters")
    digest = hmac.new(settings.JWT_SECRET.encode(), f"{user_id}:{operation}:{key}".encode(), hashlib.sha256).digest()
    return (int.from_bytes(digest[:8], "big") & ((1 << 63)-1)) or 1
