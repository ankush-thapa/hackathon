from app.core.transactions import retry_lock_conflicts
from typing import Callable

from sqlalchemy import Numeric, bindparam, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.types import DateTime3, UnsignedBigInt, UnsignedInt, UnsignedTinyInt


class RideNotFoundError(Exception):
    pass


class OwnRideError(Exception):
    pass


class RideNotBookableError(Exception):
    """Ride is not open, or has already departed."""


class NotEnoughSeatsError(Exception):
    def __init__(self, available: int):
        self.available = available
        super().__init__(f"only {available} seat(s) available")


class DuplicateBookingError(Exception):
    pass


class BookingNotFoundError(Exception):
    """No such booking, or the caller is neither its rider nor its driver (indistinguishable on purpose)."""


class NotRideDriverError(Exception):
    pass


class BookingNotPendingError(Exception):
    def __init__(self, status: str):
        self.status = status


class BookingNotCancellableError(Exception):
    def __init__(self, status: str):
        self.status = status


class RideAlreadyStartedError(Exception):
    """The ride has started, finished, or been cancelled, so its bookings can no longer change."""


_RIDE_SQL = (
    "SELECT id_ride, id_driver, status, available_seats, price_per_seat, departure_time "
    "FROM ride WHERE id_ride = :id_ride"
)
_RIDE_COLUMNS = dict(
    id_ride=UnsignedBigInt, id_driver=UnsignedBigInt, available_seats=UnsignedTinyInt,
    price_per_seat=Numeric(10, 2), departure_time=DateTime3,
)
_ACTIVE_BOOKING = text(
    "SELECT 1 FROM ride_booking WHERE id_ride = :id_ride AND id_rider = :id_rider "
    "AND status IN ('requested', 'accepted') LIMIT 1"
)
_INSERT_BOOKING = text(
    "INSERT INTO ride_booking (id_booking, id_ride, id_rider, id_driver, seats_booked, price_per_seat, "
    "total_amount, rider_note, status, version) "
    "VALUES (:id_booking, :id_ride, :id_rider, :id_driver, :seats, :price_per_seat, :total_amount, "
    ":rider_note, 'requested', 1)"
).bindparams(
    bindparam("price_per_seat", type_=Numeric(10, 2)),
    bindparam("total_amount", type_=Numeric(10, 2)),
)
_SELECT_BOOKING = text(
    "SELECT id_booking, id_ride, id_rider, id_driver, seats_booked, price_per_seat, total_amount, "
    "rider_note, status, reject_reason, cancel_reason, responded_at, cancelled_at, version, created_at, updated_at "
    "FROM ride_booking WHERE id_booking = :id_booking"
).columns(
    id_booking=UnsignedBigInt, id_ride=UnsignedBigInt, id_rider=UnsignedBigInt, id_driver=UnsignedBigInt,
    seats_booked=UnsignedTinyInt, price_per_seat=Numeric(10, 2), total_amount=Numeric(10, 2),
    responded_at=DateTime3, cancelled_at=DateTime3,
    version=UnsignedInt, created_at=DateTime3, updated_at=DateTime3,
)
_NOTIFY_CONTEXT = text(
    "SELECT r.id_driver, r.departure_time, ss.station_name AS source, ds.station_name AS destination, "
    "dp.full_name AS driver_name, rp.full_name AS rider_name "
    "FROM ride r "
    "JOIN station ss ON ss.id_station = r.id_source_station "
    "JOIN station ds ON ds.id_station = r.id_destination_station "
    "LEFT JOIN user_profile dp ON dp.id_user = r.id_driver "
    "LEFT JOIN user_profile rp ON rp.id_user = :id_rider "
    "WHERE r.id_ride = :id_ride"
).columns(departure_time=DateTime3)
_REJECT_BOOKING = text(
    "UPDATE ride_booking SET status = 'rejected', reject_reason = :reason, responded_at = :now, version = version + 1 "
    "WHERE id_booking = :id_booking AND status = 'requested'"
).bindparams(bindparam("now", type_=DateTime3))
_BOOKING_RIDE_ID = text("SELECT id_ride FROM ride_booking WHERE id_booking = :id_booking")
_LOCK_RIDE = (
    "SELECT id_ride, id_driver, status, total_seats, available_seats, departure_time FROM ride "
    "WHERE id_ride = :id_ride"
)
_LOCK_RIDE_COLUMNS = dict(
    id_ride=UnsignedBigInt, id_driver=UnsignedBigInt, total_seats=UnsignedTinyInt,
    available_seats=UnsignedTinyInt, departure_time=DateTime3,
)
_LOCK_BOOKING = "SELECT id_booking, id_rider, seats_booked, status FROM ride_booking WHERE id_booking = :id_booking"
_UPDATE_RIDE_SEATS = text(
    "UPDATE ride SET available_seats = :available_seats, status = :status, version = version + 1 "
    "WHERE id_ride = :id_ride"
)
_APPROVE_BOOKING = text(
    "UPDATE ride_booking SET status = 'accepted', responded_at = :now, version = version + 1 "
    "WHERE id_booking = :id_booking AND status = 'requested'"
).bindparams(bindparam("now", type_=DateTime3))
_CANCEL_BOOKING = text(
    "UPDATE ride_booking SET status = :status, cancel_reason = :reason, cancelled_at = :now, version = version + 1 "
    "WHERE id_booking = :id_booking AND status IN ('requested', 'accepted')"
).bindparams(bindparam("now", type_=DateTime3))


class BookingRepository:
    """Plain-SQL access to `ride_booking` (no ORM)."""

    def __init__(self, db: Session):
        self._db = db

    def _emit(self, emit: Callable[[dict], None] | None, event: str, id_ride: int, id_booking: int, id_rider: int, **extra) -> None:
        """Hand a domain event (with the names a message needs) to `emit`, inside the still-open transaction."""
        if emit is None:
            return
        c = self._db.execute(_NOTIFY_CONTEXT, {"id_ride": id_ride, "id_rider": id_rider}).mappings().one()
        emit({
            "event": event, "id_ride": id_ride, "id_booking": id_booking, "id_rider": id_rider,
            "id_driver": c["id_driver"], "route": f"{c['source']} → {c['destination']}",
            "departure_time": c["departure_time"], "rider_name": c["rider_name"], "driver_name": c["driver_name"],
            **extra,
        })

    @retry_lock_conflicts
    def create(self, params: dict, emit: Callable[[dict], None] | None = None) -> dict:
        """Validate the ride and insert a `requested` booking in one transaction.

        params: id_booking, id_ride, id_rider, seats, rider_note, now (naive UTC).
        """
        # Lock the ride row on MySQL so status/seats can't change under us. SQLite is used by the API tests.
        lock = " FOR UPDATE" if self._db.get_bind().dialect.name == "mysql" else ""
        try:
            ride = self._db.execute(text(_RIDE_SQL + lock).columns(**_RIDE_COLUMNS), params).first()
            if ride is None:
                raise RideNotFoundError
            existing_query = text(_SELECT_BOOKING.element.text + lock).columns(**{column.key: column.type for column in _SELECT_BOOKING.selected_columns})
            existing = self._db.execute(existing_query, {"id_booking": params["id_booking"]}).mappings().first()
            if existing:
                if (existing["id_rider"], existing["id_ride"], existing["seats_booked"], existing["rider_note"]) != (
                    params["id_rider"], params["id_ride"], params["seats"], params["rider_note"]
                ):
                    from fastapi import HTTPException
                    raise HTTPException(409, "Idempotency-Key already used for a different booking")
                self._db.commit()
                return dict(existing)
            if ride.id_driver == params["id_rider"]:
                raise OwnRideError
            if ride.status != "open" or ride.departure_time <= params["now"]:
                raise RideNotBookableError
            if params["seats"] > ride.available_seats:
                raise NotEnoughSeatsError(ride.available_seats)
            if self._db.execute(_ACTIVE_BOOKING, params).first():
                raise DuplicateBookingError
            self._db.execute(
                _INSERT_BOOKING,
                {
                    **params,
                    "id_driver": ride.id_driver,
                    "price_per_seat": ride.price_per_seat,  # snapshot: later price edits don't change this booking
                    "total_amount": ride.price_per_seat * params["seats"],
                },
            )
            booking = dict(self._db.execute(_SELECT_BOOKING, {"id_booking": params["id_booking"]}).mappings().one())
            self._emit(emit, "booking_requested", ride.id_ride, params["id_booking"], params["id_rider"], seats=params["seats"])
            self._db.commit()
            return booking
        except IntegrityError as error:  # uk_booking_one_active: a concurrent request won the race
            self._db.rollback()
            raise DuplicateBookingError from error
        except Exception:
            self._db.rollback()
            raise

    # ---- approve / cancel ----

    def _lock_for_change(self, id_booking: int, user_id: int):
        """Lock the ride, then the booking (always in that order, to avoid deadlocks) and re-read both.

        Raises BookingNotFoundError unless `user_id` is the booking's rider or the ride's driver.
        """
        lock = " FOR UPDATE" if self._db.get_bind().dialect.name == "mysql" else ""
        found = self._db.execute(_BOOKING_RIDE_ID, {"id_booking": id_booking}).first()
        if found is None:
            raise BookingNotFoundError
        ride = self._db.execute(
            text(_LOCK_RIDE + lock).columns(**_LOCK_RIDE_COLUMNS), {"id_ride": found.id_ride}
        ).one()
        booking = self._db.execute(text(_LOCK_BOOKING + lock), {"id_booking": id_booking}).one()
        if user_id not in (booking.id_rider, ride.id_driver):
            raise BookingNotFoundError
        return ride, booking

    def _set_ride_seats(self, ride, available_seats: int, status: str) -> None:
        self._db.execute(
            _UPDATE_RIDE_SEATS, {"id_ride": ride.id_ride, "available_seats": available_seats, "status": status}
        )

    def _read(self, id_booking: int) -> dict:
        return dict(self._db.execute(_SELECT_BOOKING, {"id_booking": id_booking}).mappings().one())

    @retry_lock_conflicts
    def approve(self, *, id_booking: int, driver_id: int, now, emit: Callable[[dict], None] | None = None) -> dict:
        """Driver accepts a `requested` booking and the seats are taken from the ride, in one transaction."""
        try:
            ride, booking = self._lock_for_change(id_booking, driver_id)
            if driver_id != ride.id_driver:
                raise NotRideDriverError
            if booking.status != "requested":
                raise BookingNotPendingError(booking.status)
            if ride.status != "open" or ride.departure_time <= now:
                raise RideNotBookableError
            if booking.seats_booked > ride.available_seats:
                raise NotEnoughSeatsError(ride.available_seats)
            remaining = ride.available_seats - booking.seats_booked
            self._set_ride_seats(ride, remaining, "full" if remaining == 0 else ride.status)
            self._db.execute(_APPROVE_BOOKING, {"id_booking": id_booking, "now": now})
            result = self._read(id_booking)
            self._emit(emit, "booking_accepted", ride.id_ride, id_booking, booking.id_rider, seats=booking.seats_booked)
            self._db.commit()
            return result
        except Exception:
            self._db.rollback()
            raise

    @retry_lock_conflicts
    def reject(
        self, *, id_booking: int, driver_id: int, reason: str | None, now, emit: Callable[[dict], None] | None = None
    ) -> dict:
        """Driver declines a `requested` booking. It never held seats, so the ride is left untouched."""
        try:
            ride, booking = self._lock_for_change(id_booking, driver_id)
            if driver_id != ride.id_driver:
                raise NotRideDriverError
            if booking.status != "requested":
                raise BookingNotPendingError(booking.status)
            if ride.status in ("started", "completed", "cancelled") or ride.departure_time <= now:
                raise RideAlreadyStartedError
            self._db.execute(_REJECT_BOOKING, {"id_booking": id_booking, "reason": reason, "now": now})
            result = self._read(id_booking)
            self._emit(emit, "booking_rejected", ride.id_ride, id_booking, booking.id_rider, seats=booking.seats_booked, reason=reason)
            self._db.commit()
            return result
        except Exception:
            self._db.rollback()
            raise

    @retry_lock_conflicts
    def cancel(
        self, *, id_booking: int, user_id: int, reason: str | None, now, emit: Callable[[dict], None] | None = None
    ) -> dict:
        """Rider or driver cancels an active booking; an accepted booking gives its seats back to the ride."""
        try:
            ride, booking = self._lock_for_change(id_booking, user_id)
            if booking.status not in ("requested", "accepted"):
                raise BookingNotCancellableError(booking.status)
            if ride.status in ("started", "completed", "cancelled"):
                raise RideAlreadyStartedError
            if booking.status == "accepted":
                restored = min(ride.total_seats, ride.available_seats + booking.seats_booked)
                self._set_ride_seats(ride, restored, "open" if ride.status == "full" else ride.status)
            self._db.execute(
                _CANCEL_BOOKING,
                {
                    "id_booking": id_booking,
                    "status": "cancelled_by_rider" if user_id == booking.id_rider else "cancelled_by_driver",
                    "reason": reason,
                    "now": now,
                },
            )
            result = self._read(id_booking)
            self._emit(
                emit, "booking_cancelled", ride.id_ride, id_booking, booking.id_rider,
                seats=booking.seats_booked, reason=reason, actor="rider" if user_id == booking.id_rider else "driver",
            )
            self._db.commit()
            return result
        except Exception:
            self._db.rollback()
            raise
