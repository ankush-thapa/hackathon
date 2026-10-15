from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import DateTime, text
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class SessionState:
    id_session: int
    id_user: int
    user_status: str
    expires_at: datetime
    revoked_at: datetime | None
    refresh_token_hash: str | None


@dataclass(frozen=True)
class SessionRow:
    id_session: int
    user_agent: str | None
    ip_address: str | None
    created_at: datetime
    expires_at: datetime


_INSERT_SESSION = text(
    "INSERT INTO user_session "
    "(id_session, id_user, user_agent, ip_address, expires_at, created_at, refresh_token_hash) "
    "VALUES (:id_session, :id_user, :user_agent, :ip_address, :expires_at, :created_at, :refresh_token_hash)"
)
# Typed columns so SQLite returns datetimes, not strings.
_GET_STATE = text(
    "SELECT s.id_session, s.id_user, u.status, s.expires_at, s.revoked_at, s.refresh_token_hash "
    "FROM user_session s JOIN `user` u ON u.id_user = s.id_user WHERE s.id_session = :id_session"
).columns(expires_at=DateTime, revoked_at=DateTime)
_LIST_ACTIVE = text(
    "SELECT id_session, user_agent, ip_address, created_at, expires_at FROM user_session "
    "WHERE id_user = :id_user AND revoked_at IS NULL AND expires_at > :now ORDER BY created_at DESC, id_session DESC"
).columns(created_at=DateTime, expires_at=DateTime)
_REVOKE = text(
    "UPDATE user_session SET revoked_at = :now "
    "WHERE id_session = :id_session AND id_user = :id_user AND revoked_at IS NULL AND expires_at > :now"
)
_ROTATE_REFRESH = text(
    "UPDATE user_session SET refresh_token_hash = :new_hash "
    "WHERE id_session = :id_session AND refresh_token_hash = :old_hash AND revoked_at IS NULL AND expires_at > :now"
)


class SessionRepository:
    """Plain-SQL access to the `user_session` table. All datetimes are naive UTC."""

    def __init__(self, db: Session):
        self._db = db

    def create(
        self, id_session: int, id_user: int, user_agent: str | None, ip_address: str | None,
        created_at: datetime, expires_at: datetime, refresh_token_hash: str, expected_password_hash: str | None = None,
    ) -> None:
        lock = " FOR UPDATE" if self._db.get_bind().dialect.name == "mysql" else ""
        user = self._db.execute(text("SELECT status, password_hash FROM `user` WHERE id_user = :id_user" + lock), {"id_user": id_user}).first()
        if user is None or user.status != "active" or (expected_password_hash is not None and user.password_hash != expected_password_hash):
            self._db.rollback()
            from fastapi import HTTPException
            raise HTTPException(403, "account inactive")
        self._db.execute(
            _INSERT_SESSION,
            {
                "id_session": id_session, "id_user": id_user, "user_agent": user_agent,
                "ip_address": ip_address, "created_at": created_at, "expires_at": expires_at,
                "refresh_token_hash": refresh_token_hash,
            },
        )
        self._db.commit()

    def get_state(self, id_session: int) -> SessionState | None:
        row = self._db.execute(_GET_STATE, {"id_session": id_session}).first()
        if row is None:
            return None
        return SessionState(
            row.id_session, row.id_user, row.status, row.expires_at, row.revoked_at, row.refresh_token_hash
        )

    def list_active(self, id_user: int, now: datetime) -> list[SessionRow]:
        rows = self._db.execute(_LIST_ACTIVE, {"id_user": id_user, "now": now})
        return [SessionRow(r.id_session, r.user_agent, r.ip_address, r.created_at, r.expires_at) for r in rows]

    def revoke(self, id_session: int, id_user: int, now: datetime) -> bool:
        """Revoke one of the user's live sessions. False if it is not theirs or already ended."""
        revoked = self._db.execute(_REVOKE, {"id_session": id_session, "id_user": id_user, "now": now}).rowcount
        self._db.commit()
        return revoked == 1

    def rotate_refresh(self, id_session: int, old_hash: str, new_hash: str, now: datetime) -> bool:
        """Swap the refresh hash only if `old_hash` is still current, so a token can be used once."""
        params = {"id_session": id_session, "old_hash": old_hash, "new_hash": new_hash, "now": now}
        rotated = self._db.execute(_ROTATE_REFRESH, params).rowcount
        self._db.commit()
        return rotated == 1
