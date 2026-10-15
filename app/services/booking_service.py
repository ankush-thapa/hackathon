from datetime import datetime, timezone

from app.core.ids import new_id
from app.repositories.booking_repo import BookingRepository
from app.schemas.booking import BookRideRequest


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)  # DATETIME(3) stores naive UTC


class BookingService:
    def __init__(self, bookings: BookingRepository):
        self._bookings = bookings

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
            }
        )

    def approve(self, driver_id: int, id_booking: int) -> dict:
        """The ride's driver accepts a requested booking, taking its seats from the ride."""
        return self._bookings.approve(id_booking=id_booking, driver_id=driver_id, now=_now())

    def cancel(self, user_id: int, id_booking: int, reason: str | None) -> dict:
        """Rider or driver cancels an active booking; an accepted one gives its seats back."""
        return self._bookings.cancel(id_booking=id_booking, user_id=user_id, reason=reason, now=_now())
