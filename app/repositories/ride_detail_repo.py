from sqlalchemy import text
from sqlalchemy.orm import Session

from app.repositories.ride_sql import RIDE_COLUMNS, RIDE_JOINS

_RIDE = text(
    f"""SELECT {RIDE_COLUMNS},
       (SELECT COUNT(*) FROM ride_booking b
         WHERE b.id_ride = r.id_ride AND b.status = 'requested') AS pending_requests,
       (SELECT COALESCE(SUM(b.seats_booked), 0) FROM ride_booking b
         WHERE b.id_ride = r.id_ride AND b.status = 'accepted') AS accepted_seats
FROM ride r {RIDE_JOINS}
WHERE r.id_ride = :id_ride"""
)
# My active booking wins; otherwise my most recent one.
_MY_BOOKING = text(
    "SELECT id_booking, status, seats_booked, price_per_seat, total_amount, rider_note, created_at "
    "FROM ride_booking WHERE id_ride = :id_ride AND id_rider = :id_user "
    "ORDER BY (CASE WHEN status IN ('requested', 'accepted') THEN 1 ELSE 0 END) DESC, created_at DESC, id_booking DESC "
    "LIMIT 1"
)
_ACTIVE_BOOKINGS = text(
    "SELECT b.id_booking, b.id_rider, b.status, b.seats_booked, b.price_per_seat, b.total_amount, b.rider_note, "
    "b.created_at, p.full_name AS rider_name, p.photo_url AS rider_photo_url "
    "FROM ride_booking b LEFT JOIN user_profile p ON p.id_user = b.id_rider "
    "WHERE b.id_ride = :id_ride AND b.status IN ('requested', 'accepted') "
    "ORDER BY b.created_at, b.id_booking"
)


class RideDetailRepository:
    """Plain-SQL reads for a single ride (no ORM)."""

    def __init__(self, db: Session):
        self._db = db

    def get_ride(self, id_ride: int) -> dict | None:
        row = self._db.execute(_RIDE, {"id_ride": id_ride}).mappings().first()
        return dict(row) if row else None

    def get_my_booking(self, id_ride: int, id_user: int) -> dict | None:
        row = self._db.execute(_MY_BOOKING, {"id_ride": id_ride, "id_user": id_user}).mappings().first()
        return dict(row) if row else None

    def list_active_bookings(self, id_ride: int) -> list[dict]:
        return [dict(r) for r in self._db.execute(_ACTIVE_BOOKINGS, {"id_ride": id_ride}).mappings().all()]
