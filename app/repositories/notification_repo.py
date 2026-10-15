from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.types import DateTime3, UnsignedBigInt

_COLUMNS = "id_notification, type, id_ride, id_booking, message, is_read, created_at"
# Served by idx_notification_user (id_user, is_read, created_at). Typed so SQLite returns datetimes.
_LIST_UNREAD = text(
    f"SELECT {_COLUMNS} FROM notification WHERE id_user = :id_user AND is_read = 0 "
    "ORDER BY created_at DESC, id_notification DESC LIMIT :limit"
).columns(id_notification=UnsignedBigInt, id_ride=UnsignedBigInt, id_booking=UnsignedBigInt, created_at=DateTime3)
_COUNT_UNREAD = text("SELECT COUNT(*) FROM notification WHERE id_user = :id_user AND is_read = 0")
_INSERT = text(
    "INSERT INTO notification (id_notification, id_user, type, id_ride, id_booking, message, is_read) "
    "VALUES (:id_notification, :id_user, :type, :id_ride, :id_booking, :message, 0)"
)
_EXISTS = text("SELECT 1 FROM notification WHERE id_notification = :id_notification AND id_user = :id_user")
_MARK_READ = text(
    "UPDATE notification SET is_read = 1 WHERE id_notification = :id_notification AND id_user = :id_user"
)
_GET = text(f"SELECT {_COLUMNS} FROM notification WHERE id_notification = :id_notification").columns(
    id_notification=UnsignedBigInt, id_ride=UnsignedBigInt, id_booking=UnsignedBigInt, created_at=DateTime3
)
_RIDE_DRIVER = text("SELECT id_driver FROM ride WHERE id_ride = :id_ride")
_RIDE_RIDERS = text("SELECT DISTINCT id_rider FROM ride_booking WHERE id_ride = :id_ride")
_BOOKING_ON_RIDE = text("SELECT 1 FROM ride_booking WHERE id_booking = :id_booking AND id_ride = :id_ride")
_MARK_ALL_READ = text("UPDATE notification SET is_read = 1 WHERE id_user = :id_user AND is_read = 0")


class NotificationRepository:
    """Plain-SQL access to `notification`, always scoped to the recipient."""

    def __init__(self, db: Session):
        self._db = db

    def add(self, params: dict) -> None:
        """Insert without committing, so the notification lands in the caller's transaction."""
        self._db.execute(_INSERT, params)

    def get(self, id_notification: int) -> dict | None:
        row = self._db.execute(_GET, {"id_notification": id_notification}).mappings().first()
        return dict(row) if row else None

    def commit(self) -> None:
        self._db.commit()

    def ride_participants(self, id_ride: int) -> set[int] | None:
        """Driver plus every rider who booked the ride; None if the ride does not exist."""
        id_driver = self._db.execute(_RIDE_DRIVER, {"id_ride": id_ride}).scalar()
        if id_driver is None:
            return None
        riders = self._db.execute(_RIDE_RIDERS, {"id_ride": id_ride}).scalars()
        return {id_driver, *riders}

    def booking_on_ride(self, id_booking: int, id_ride: int) -> bool:
        return self._db.execute(_BOOKING_ON_RIDE, {"id_booking": id_booking, "id_ride": id_ride}).first() is not None

    def list_unread(self, id_user: int, limit: int) -> list[dict]:
        rows = self._db.execute(_LIST_UNREAD, {"id_user": id_user, "limit": limit}).mappings().all()
        return [dict(r) for r in rows]

    def count_unread(self, id_user: int) -> int:
        return self._db.execute(_COUNT_UNREAD, {"id_user": id_user}).scalar_one()

    def mark_read(self, id_user: int, id_notification: int) -> bool:
        """False if the notification does not exist or belongs to someone else. Idempotent otherwise."""
        params = {"id_user": id_user, "id_notification": id_notification}
        if self._db.execute(_EXISTS, params).first() is None:
            return False
        self._db.execute(_MARK_READ, params)
        self._db.commit()
        return True

    def mark_all_read(self, id_user: int) -> int:
        count = self._db.execute(_MARK_ALL_READ, {"id_user": id_user}).rowcount
        self._db.commit()
        return count
