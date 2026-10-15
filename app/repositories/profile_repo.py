from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


class UserNotFoundError(Exception):
    pass


_USER_EXISTS = text("SELECT 1 FROM `user` WHERE id_user = :id_user LIMIT 1")
_PROFILE_EXISTS = text("SELECT 1 FROM user_profile WHERE id_user = :id_user LIMIT 1")
_INSERT_PROFILE = text(
    "INSERT INTO user_profile (id_user, full_name, photo_url, about, date_of_birth, gender) "
    "VALUES (:id_user, :full_name, :photo_url, :about, :date_of_birth, :gender)"
)
_UPDATE_PROFILE = text(
    "UPDATE user_profile SET full_name = :full_name, photo_url = :photo_url, about = :about, "
    "date_of_birth = :date_of_birth, gender = :gender WHERE id_user = :id_user"
)


class ProfileRepository:
    """Plain-SQL access to the `user_profile` table (no ORM)."""

    def __init__(self, db: Session):
        self._db = db

    def upsert(self, params: dict) -> bool:
        """Create or fully replace the profile. Returns True if a new row was created."""
        if not self._db.execute(_USER_EXISTS, {"id_user": params["id_user"]}).first():
            raise UserNotFoundError
        if self._db.execute(_PROFILE_EXISTS, {"id_user": params["id_user"]}).first():
            self._update(params)
            return False
        try:
            self._db.execute(_INSERT_PROFILE, params)
            self._db.commit()
            return True
        except IntegrityError:  # lost a race with a concurrent insert (PK on id_user): update instead
            self._db.rollback()
            if not self._db.execute(_PROFILE_EXISTS, {"id_user": params["id_user"]}).first():
                raise UserNotFoundError from None  # FK failed: user vanished between check and insert
            self._update(params)
            return False

    def _update(self, params: dict) -> None:
        self._db.execute(_UPDATE_PROFILE, params)
        self._db.commit()
