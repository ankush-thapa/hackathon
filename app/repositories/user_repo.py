from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


class DuplicateUserError(Exception):
    def __init__(self, field: str):
        self.field = field
        super().__init__(f"{field} already registered")


@dataclass(frozen=True)
class NewUser:
    id_user: int
    email: str
    phone_number: str


_INSERT_USER = text(
    "INSERT INTO `user` (id_user, email, phone_number, password_hash) "
    "VALUES (:id_user, :email, :phone_number, :password_hash)"
)
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

    def _conflicting_field(self, email: str, phone_number: str) -> str:
        if self._db.execute(_EXISTS_BY_EMAIL, {"v": email}).first():
            return "email"
        if self._db.execute(_EXISTS_BY_PHONE, {"v": phone_number}).first():
            return "phone"
        return "user"
