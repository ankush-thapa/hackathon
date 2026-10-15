from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import DateTime, text
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class ActiveSession:
    id_session: int
    id_user: int
    user_status: str


@dataclass(frozen=True)
class SessionRow:
    id_session: int
    user_agent: str | None
    ip_address: str | None
    created_at: datetime
    expires_at: datetime


_INSERT_SESSION = text(
    "INSERT INTO user_session (id_session, id_user, user_agent, ip_address, expires_at, created_at) "
    "VALUES (:id_session, :id_user, :user_agent, :ip_address, :expires_at, :created_at)"
)
_GET_ACTIVE = text(
    "SELECT s.id_session, s.id_user, u.status FROM user_session s JOIN `user` u ON u.id_user = s.id_user "
    "WHERE s.id_session = :id_session AND s.revoked_at IS NULL AND s.expires_at > :now"
)
_LIST_ACTIVE = text(
    "SELECT id_session, user_agent, ip_address, created_at, expires_at FROM user_session "
    "WHERE id_user = :id_user AND revoked_at IS NULL AND expires_at > :now ORDER BY created_at DESC, id_session DESC"
).columns(created_at=DateTime, expires_at=DateTime)  # typed so SQLite returns datetimes, not strings
_REVOKE = text(
    "UPDATE user_session SET revoked_at = :now "
    "WHERE id_session = :id_session AND id_user = :id_user AND revoked_at IS NULL AND expires_at > :now"
)


class SessionRepository:
    """Plain-SQL access to the `user_session` table. All datetimes are naive UTC."""

    def __init__(self, db: Session):
        self._db = db

    def create(
        self, id_session: int, id_user: int, user_agent: str | None, ip_address: str | None,
        created_at: datetime, expires_at: datetime,
    ) -> None:
        self._db.execute(
            _INSERT_SESSION,
            {
                "id_session": id_session, "id_user": id_user, "user_agent": user_agent,
                "ip_address": ip_address, "created_at": created_at, "expires_at": expires_at,
            },
        )
        self._db.commit()

    def get_active(self, id_session: int, now: datetime) -> ActiveSession | None:
        row = self._db.execute(_GET_ACTIVE, {"id_session": id_session, "now": now}).first()
        return ActiveSession(row.id_session, row.id_user, row.status) if row else None

    def list_active(self, id_user: int, now: datetime) -> list[SessionRow]:
        rows = self._db.execute(_LIST_ACTIVE, {"id_user": id_user, "now": now})
        return [SessionRow(r.id_session, r.user_agent, r.ip_address, r.created_at, r.expires_at) for r in rows]

    def revoke(self, id_session: int, id_user: int, now: datetime) -> bool:
        """Revoke one of the user's live sessions. False if it is not theirs or already ended."""
        revoked = self._db.execute(_REVOKE, {"id_session": id_session, "id_user": id_user, "now": now}).rowcount
        self._db.commit()
        return revoked == 1
