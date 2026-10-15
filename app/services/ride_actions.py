from app.core.transactions import retry_lock_conflicts
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Ride, RideStatus, RideBooking, BookingStatus, Vehicle, Station, UserProfile
from app.models.notification import NotificationType
from app.repositories.ride_schedule import lock_driver, ensure_departure_gap
from app.repositories.notification_repo import NotificationRepository
from app.schemas.ride import OfferRideRequest
from app.services.notification_service import NotificationService


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class RideActions:
    """All mutations lock the ride first, then its bookings, in one transaction."""
    def __init__(self, db: Session):
        self.db = db

    def ride(self, ride_id, user_id, owner=False):
        ride = self.db.scalar(select(Ride).where(Ride.id_ride == ride_id).with_for_update())
        if ride is None or (owner and ride.id_driver != user_id):
            raise HTTPException(404, "ride not found")
        return ride

    def notify(self, recipient, kind, ride, message, booking=None):
        NotificationService(NotificationRepository(self.db)).notify(
            recipient, NotificationType(kind), ride.id_ride, message,
            booking.id_booking if booking else None,
        )

    @staticmethod
    def release_seats(ride, seats):
        """A pending request holds its seats; give them back (capped at total_seats) and reopen a full ride."""
        ride.available_seats = min(ride.total_seats, ride.available_seats + seats)
        if ride.status == RideStatus.full:
            ride.status = RideStatus.open

    def detail(self, ride_id):
        ride = self.db.get(Ride, ride_id)
        if ride is None:
            raise HTTPException(404, "ride not found")
        return ride

    def booking(self, booking_id, user_id):
        b = self.db.get(RideBooking, booking_id)
        if b is None or user_id not in (b.id_rider, b.id_driver):
            raise HTTPException(404, "booking not found")
        return b

    def list_bookings(self, ride_id, user_id, status, after, limit):
        ride = self.db.get(Ride, ride_id)
        if ride is None or ride.id_driver != user_id:
            raise HTTPException(404, "ride not found")
        query = (select(RideBooking, UserProfile.full_name, UserProfile.photo_url)
                 .outerjoin(UserProfile, UserProfile.id_user == RideBooking.id_rider)
                 .where(RideBooking.id_ride == ride_id))
        if status is not None:
            query = query.where(RideBooking.status == status)
        if after is not None:
            query = query.where(RideBooking.id_booking < after)
        rows = self.db.execute(query.order_by(RideBooking.id_booking.desc()).limit(limit+1)).all()
        return rows[:limit], str(rows[limit-1][0].id_booking) if len(rows)>limit else None

    @retry_lock_conflicts
    def reject(self, booking_id, user_id, reason):
        try:
            found = self.db.get(RideBooking, booking_id)
            if found is None:
                raise HTTPException(404, "booking not found")
            ride = self.ride(found.id_ride, user_id, owner=True)
            b = self.db.scalar(select(RideBooking).where(RideBooking.id_booking == booking_id)
                               .with_for_update().execution_options(populate_existing=True))
            if b.status == BookingStatus.rejected:
                return b
            if b.status != BookingStatus.requested or ride.status not in (RideStatus.open, RideStatus.full) or ride.departure_time <= now():
                raise HTTPException(409, "booking cannot be rejected in its current state")
            b.status = BookingStatus.rejected
            b.reject_reason = reason
            b.responded_at = now()
            self.release_seats(ride, b.seats_booked)
            self.notify(b.id_rider, "booking_rejected", ride, "Your ride request was declined", b)
            self.db.commit()
            return b
        except Exception:
            self.db.rollback()
            raise

    @retry_lock_conflicts
    def update(self, ride_id, user_id, request):
        try:
            lock_driver(self.db, user_id)
            ride = self.ride(ride_id, user_id, owner=True)
            if ride.status not in (RideStatus.open, RideStatus.full) or ride.departure_time <= now():
                raise HTTPException(409, "only future open/full rides can be edited")
            changes = request.model_dump(exclude_unset=True)
            active = list(self.db.scalars(select(RideBooking).where(
                RideBooking.id_ride == ride_id,
                RideBooking.status.in_([BookingStatus.requested, BookingStatus.accepted]),
            ).with_for_update()))
            protected = {"id_vehicle", "id_source_station", "id_destination_station", "departure_time", "price_per_seat"}
            if active and protected & changes.keys():
                raise HTTPException(409, "cancel active requests/bookings before changing vehicle, route, departure or price")
            values = {key: getattr(ride,key) for key in OfferRideRequest.model_fields}
            for key in ("departure_time", "estimated_arrival_time"):
                if values[key]: values[key] = values[key].replace(tzinfo=timezone.utc)
            validated = OfferRideRequest.model_validate({**values, **changes})
            if validated.departure_time.replace(tzinfo=None) <= now():
                raise HTTPException(422, "departure_time must be in the future")
            if "departure_time" in changes:
                ensure_departure_gap(self.db, user_id, validated.departure_time.replace(tzinfo=None), ride_id)
            vehicle = self.db.scalar(select(Vehicle).where(Vehicle.id_vehicle == validated.id_vehicle).with_for_update())
            if vehicle is None or vehicle.id_user != user_id or vehicle.status != "active":
                raise HTTPException(422, "vehicle must be active and owned by the driver")
            if validated.total_seats > vehicle.seat_capacity:
                raise HTTPException(422, "total_seats exceeds vehicle capacity")
            for station_id in (validated.id_source_station, validated.id_destination_station):
                station = self.db.get(Station, station_id)
                if station is None or not station.is_active:
                    raise HTTPException(422, "station is missing or inactive")
            held = sum(b.seats_booked for b in active)  # pending requests hold seats too
            if validated.total_seats < held:
                raise HTTPException(409, "total_seats cannot be below seats held by requests and bookings")
            for key, value in validated.model_dump().items():
                if isinstance(value, datetime): value=value.replace(tzinfo=None)
                setattr(ride, key, value)
            ride.available_seats = ride.total_seats - held
            ride.status = RideStatus.full if ride.available_seats == 0 else RideStatus.open
            for b in active:
                self.notify(b.id_rider, "ride_modified", ride, "Your ride details changed", b)
            self.db.commit()
            return ride
        except Exception:
            self.db.rollback()
            raise

    @retry_lock_conflicts
    def transition(self, ride_id, user_id, action, reason=None):
        try:
            ride = self.ride(ride_id, user_id, owner=True)
            target = {"cancel": RideStatus.cancelled, "start": RideStatus.started, "complete": RideStatus.completed}[action]
            if ride.status == target:
                return ride
            allowed = (RideStatus.open, RideStatus.full) if action in ("cancel", "start") else (RideStatus.started,)
            if ride.status not in allowed:
                raise HTTPException(409, f"ride cannot {action} from {ride.status.value}")
            if action == "start" and ride.departure_time > now():
                raise HTTPException(409, "ride cannot start before its scheduled departure")
            bookings = list(self.db.scalars(select(RideBooking).where(
                RideBooking.id_ride == ride_id,
                RideBooking.status.in_([BookingStatus.requested, BookingStatus.accepted]),
            ).with_for_update()))
            released = 0
            for b in bookings:
                if action == "cancel":
                    b.status = BookingStatus.cancelled_by_driver
                    b.cancel_reason = reason
                    b.cancelled_at = now()
                    self.notify(b.id_rider, "ride_cancelled", ride, "The driver cancelled your ride", b)
                elif b.status == BookingStatus.requested:
                    b.status = BookingStatus.expired
                    b.responded_at = now()
                    released += b.seats_booked
                    self.notify(b.id_rider, "booking_rejected", ride, "Your pending ride request expired", b)
                elif action == "complete":
                    b.status = BookingStatus.completed
            ride.status = target
            if released:
                ride.available_seats = min(ride.total_seats, ride.available_seats + released)
            if action == "cancel":
                ride.cancel_reason = reason
                ride.cancelled_at = now()
                ride.available_seats = ride.total_seats
            self.db.commit()
            return ride
        except Exception:
            self.db.rollback()
            raise

    @retry_lock_conflicts
    def expire(self, ride_id, user_id):
        try:
            ride = self.ride(ride_id, user_id, owner=True)
            if ride.departure_time > now():
                raise HTTPException(409, "requests expire only after departure")
            rows = list(self.db.scalars(select(RideBooking).where(
                RideBooking.id_ride == ride_id, RideBooking.status == BookingStatus.requested,
            ).with_for_update()))
            for b in rows:
                b.status = BookingStatus.expired
                b.responded_at = now()
                self.release_seats(ride, b.seats_booked)
                self.notify(b.id_rider, "booking_rejected", ride, "Your pending ride request expired", b)
            self.db.commit()
            return len(rows)
        except Exception:
            self.db.rollback()
            raise
