from app.repositories.ride_detail_repo import RideDetailRepository
from app.schemas.my_ride import RideRequestsInfo
from app.schemas.ride_detail import BookingBrief, RideBookingInfo, RideDetailResponse, RideRole, RiderInfo
from app.services.ride_view import money, ride_fields, utc

# Rides anyone logged in may look at (the ones a search can show). Anything else is only for the people involved.
_PUBLIC_STATUSES = ("open", "full")


class RideNotFoundError(Exception):
    """No such ride, or the caller is not allowed to see it (indistinguishable on purpose)."""


def _booking_fields(b: dict) -> dict:
    return dict(
        id_booking=str(b["id_booking"]),
        status=b["status"],
        seats_booked=b["seats_booked"],
        price_per_seat=money(b["price_per_seat"]),
        total_amount=money(b["total_amount"]),
        rider_note=b["rider_note"],
        created_at=utc(b["created_at"]),
    )


class RideDetailService:
    def __init__(self, rides: RideDetailRepository):
        self._rides = rides

    def get(self, id_ride: int, id_user: int) -> RideDetailResponse:
        """Details of one ride as seen by `id_user`. Raises RideNotFoundError."""
        ride = self._rides.get_ride(id_ride)
        if ride is None:
            raise RideNotFoundError
        mine = self._rides.get_my_booking(id_ride, id_user)
        if ride["id_driver"] == id_user:
            role = RideRole.driver
        elif mine is not None:
            role = RideRole.rider
        else:
            role = RideRole.viewer
        if role is RideRole.viewer and ride["ride_status"] not in _PUBLIC_STATUSES:
            raise RideNotFoundError

        is_driver = role is RideRole.driver
        return RideDetailResponse(
            **ride_fields(ride),
            role=role,
            my_booking=BookingBrief(**_booking_fields(mine)) if mine else None,
            requests=RideRequestsInfo(pending_requests=ride["pending_requests"], accepted_seats=int(ride["accepted_seats"]))
            if is_driver
            else None,
            bookings=[
                RideBookingInfo(
                    **_booking_fields(b),
                    rider=RiderInfo(id_user=str(b["id_rider"]), full_name=b["rider_name"], photo_url=b["rider_photo_url"]),
                )
                for b in self._rides.list_active_bookings(id_ride)
            ]
            if is_driver
            else None,
        )
