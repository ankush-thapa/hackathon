from app.core.transactions import retry_lock_conflicts
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import or_, select, update
from sqlalchemy.exc import IntegrityError

from app.core.security import hash_password, verify_password
from app.models import User, UserStatus, UserSession, UserDocument, Vehicle, Ride, RideStatus, RideBooking, BookingStatus
from app.models.notification import NotificationType
from app.repositories.notification_repo import NotificationRepository
from app.services.notification_service import NotificationService


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AccountService:
    def __init__(self, db):
        self.db = db

    def _user(self, user_id, password):
        user = self.db.scalar(select(User).where(User.id_user == user_id).with_for_update())
        if user is None or user.status != UserStatus.active or not verify_password(password, user.password_hash):
            raise HTTPException(403, "current password is incorrect or account inactive")
        return user

    @retry_lock_conflicts
    def contacts(self, user_id, req):
        try:
            user = self._user(user_id, req.current_password)
            if "email" in req.model_fields_set: user.email = req.email
            if "phone" in req.model_fields_set: user.phone_number = req.phone
            self.db.commit()
            return {"userId": str(user.id_user), "email": user.email, "phone": user.phone_number, "status": user.status.value}
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(409, "email or phone already registered") from None
        except Exception:
            self.db.rollback()
            raise

    @retry_lock_conflicts
    def password(self, user_id, req):
        try:
            user = self._user(user_id, req.current_password)
            if verify_password(req.new_password, user.password_hash):
                raise HTTPException(422, "new password must differ from current password")
            user.password_hash = hash_password(req.new_password)
            self.db.execute(update(UserSession).where(UserSession.id_user == user_id, UserSession.revoked_at.is_(None))
                            .values(revoked_at=now()))
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    @retry_lock_conflicts
    def delete(self, user_id, password):
        try:
            # Lock rides in a stable order before changing bookings or the account.
            booked = select(RideBooking.id_ride).where(RideBooking.id_rider == user_id,
                         RideBooking.status.in_([BookingStatus.requested, BookingStatus.accepted]))
            rides = list(self.db.scalars(select(Ride).where(
                or_(Ride.id_driver == user_id, Ride.id_ride.in_(booked)),
                Ride.status.in_([RideStatus.open, RideStatus.full, RideStatus.started]),
            ).order_by(Ride.id_ride).with_for_update()))
            if any(r.status == RideStatus.started for r in rides):
                raise HTTPException(409, "finish active rides before deleting the account")
            user = self._user(user_id, password)
            notifications = NotificationService(NotificationRepository(self.db))
            for ride in rides:
                rows = list(self.db.scalars(select(RideBooking).where(
                    RideBooking.id_ride == ride.id_ride,
                    RideBooking.status.in_([BookingStatus.requested, BookingStatus.accepted]),
                ).order_by(RideBooking.id_booking).with_for_update()))
                for b in rows:
                    if ride.id_driver != user_id and b.id_rider != user_id:
                        continue
                    accepted = b.status == BookingStatus.accepted
                    driver_deleted = ride.id_driver == user_id
                    b.status = BookingStatus.cancelled_by_driver if driver_deleted else BookingStatus.cancelled_by_rider
                    b.cancel_reason = "Account deleted"
                    b.cancelled_at = now()
                    recipient = b.id_rider if driver_deleted else ride.id_driver
                    notifications.notify(recipient, NotificationType.ride_cancelled if driver_deleted else NotificationType.booking_cancelled,
                                         ride.id_ride, "Ride/booking cancelled because a participant deleted their account", b.id_booking)
                    if accepted and not driver_deleted:
                        ride.available_seats += b.seats_booked
                        if ride.status == RideStatus.full: ride.status = RideStatus.open
                if ride.id_driver == user_id:
                    ride.status = RideStatus.cancelled
                    ride.cancel_reason = "Account deleted"
                    ride.cancelled_at = now()
                    ride.available_seats = ride.total_seats
            user.status = UserStatus.deleted
            self.db.execute(update(UserSession).where(UserSession.id_user == user_id, UserSession.revoked_at.is_(None)).values(revoked_at=now()))
            self.db.execute(update(Vehicle).where(Vehicle.id_user == user_id).values(status="deleted", is_default=False))
            self.db.execute(update(UserDocument).where(UserDocument.id_user == user_id).values(is_active=False))
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
