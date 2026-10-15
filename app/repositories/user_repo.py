from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


class DuplicateUserError(Exception):
    def __init__(self, field: str):
        self.field = field
        super().__init__(f"{field} already registered")


@dataclass(frozen=True)
class UserCredentials:
    id_user: int
    password_hash: str
    status: str


@dataclass(frozen=True)
class NewUser:
    id_user: int
    email: str
    phone_number: str


_INSERT_USER = text(
    "INSERT INTO `user` (id_user, email, phone_number, password_hash) "
    "VALUES (:id_user, :email, :phone_number, :password_hash)"
)
_CREDENTIALS_BY_EMAIL = text("SELECT id_user, password_hash, status FROM `user` WHERE email = :v")
_CREDENTIALS_BY_PHONE = text("SELECT id_user, password_hash, status FROM `user` WHERE phone_number = :v")
_TOUCH_LAST_ACTIVE = text("UPDATE `user` SET last_active = :now WHERE id_user = :id_user")
_EXISTS_BY_EMAIL = text("SELECT 1 FROM `user` WHERE email = :v LIMIT 1")
_EXISTS_BY_PHONE = text("SELECT 1 FROM `user` WHERE phone_number = :v LIMIT 1")


class UserRepository:
    """Plain-SQL access to the `user` table (no ORM)."""

    def __init__(self, db: Session):
        self._db = db

    def create(self, id_user: int, email: str, phone_number: str, password_hash: str) -> NewUser:
        try:
            self._db.execute(
                _INSERT_USER,
                {"id_user": id_user, "email": email, "phone_number": phone_number, "password_hash": password_hash},
            )
            self._db.commit()  # unique keys are the source of truth, so this is race-safe
        except IntegrityError:
            self._db.rollback()
            raise DuplicateUserError(self._conflicting_field(email, phone_number)) from None
        return NewUser(id_user=id_user, email=email, phone_number=phone_number)

    def get_credentials(self, *, email: str | None = None, phone_number: str | None = None) -> UserCredentials | None:
        query, value = (_CREDENTIALS_BY_EMAIL, email) if email is not None else (_CREDENTIALS_BY_PHONE, phone_number)
        row = self._db.execute(query, {"v": value}).first()
        return UserCredentials(row.id_user, row.password_hash, row.status) if row else None

    def touch_last_active(self, id_user: int, now: datetime) -> None:
        self._db.execute(_TOUCH_LAST_ACTIVE, {"id_user": id_user, "now": now})
        self._db.commit()

    def _conflicting_field(self, email: str, phone_number: str) -> str:
        if self._db.execute(_EXISTS_BY_EMAIL, {"v": email}).first():
            return "email"
        if self._db.execute(_EXISTS_BY_PHONE, {"v": phone_number}).first():
            return "phone"
        return "user"
