from datetime import datetime, timezone

from app.core.ids import new_id
from app.repositories.booking_repo import BookingRepository
from app.schemas.booking import BookRideRequest
from app.services.notification_events import notify_event
from app.services.notification_service import NotificationService


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)  # DATETIME(3) stores naive UTC


class BookingService:
    def __init__(self, bookings: BookingRepository, notifications: NotificationService | None = None):
        self._bookings = bookings
        self._notifications = notifications

    def _emit(self, ctx: dict) -> None:
        """Called by the repository just before it commits, so notifications share the change's transaction."""
        notify_event(self._notifications, ctx)

    @property
    def _hook(self):
        return self._emit if self._notifications is not None else None

    def book(self, rider_id: int, request: BookRideRequest) -> dict:
        """Create a `requested` booking. Seats are held only once the driver accepts."""
        return self._bookings.create(
            {
                "id_booking": new_id(),
                "id_ride": request.id_ride,
                "id_rider": rider_id,
                "seats": request.seats,
                "rider_note": request.rider_note,
                "now": _now(),
            },
            emit=self._hook,
        )

    def approve(self, driver_id: int, id_booking: int) -> dict:
        """The ride's driver accepts a requested booking, taking its seats from the ride."""
        return self._bookings.approve(id_booking=id_booking, driver_id=driver_id, now=_now(), emit=self._hook)

    def cancel(self, user_id: int, id_booking: int, reason: str | None) -> dict:
        """Rider or driver cancels an active booking; an accepted one gives its seats back."""
        return self._bookings.cancel(id_booking=id_booking, user_id=user_id, reason=reason, now=_now(), emit=self._hook)

    def reject(self, driver_id: int, id_booking: int, reason: str | None) -> dict:
        """The ride's driver declines a requested booking."""
        return self._bookings.reject(id_booking=id_booking, driver_id=driver_id, reason=reason, now=_now(), emit=self._hook)
