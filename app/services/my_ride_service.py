from datetime import datetime, timezone

from app.core.pagination import decode_cursor, paginate
from app.repositories.my_ride_repo import MyRideRepository
from app.schemas.my_ride import (
    MyBookingItem,
    MyBookingsResponse,
    MyRideItem,
    MyRidesResponse,
    MyRideScope,
    RideInfo,
    RideRequestsInfo,
)
from app.services.ride_view import money as _money
from app.services.ride_view import ride_fields as _ride_fields
from app.services.ride_view import utc as _utc


class MyRideService:
    def __init__(self, rides: MyRideRepository):
        self._rides = rides

    def _fetch(self, fetch, id_user: int, scope: MyRideScope, page_size: int, cursor: str | None):
        direction, position = None, None
        if cursor:  # raises InvalidCursorError
            direction, *position = decode_cursor(cursor)
            position = tuple(position)
        rows = fetch(
            id_user=id_user,
            scope=scope.value,
            now=datetime.now(timezone.utc).replace(tzinfo=None),
            position=position,
            going_back=direction == "p",
            limit=page_size + 1,  # one extra row tells us whether another page exists
        )
        return paginate(rows, page_size, direction, lambda r: (r["departure_time"], r["row_id"]))

    def list_offered(self, *, id_user: int, scope: MyRideScope, page_size: int, cursor: str | None) -> MyRidesResponse:
        """Rides the caller offered as a driver. Raises InvalidCursorError."""
        page, next_page, prev_page = self._fetch(self._rides.list_offered, id_user, scope, page_size, cursor)
        items = [
            MyRideItem(
                **_ride_fields(r),
                requests=RideRequestsInfo(pending_requests=r["pending_requests"], accepted_seats=int(r["accepted_seats"])),
            )
            for r in page
        ]
        return MyRidesResponse(items=items, next_page=next_page, prev_page=prev_page)

    def list_booked(self, *, id_user: int, scope: MyRideScope, page_size: int, cursor: str | None) -> MyBookingsResponse:
        """Bookings the caller made as a rider. Raises InvalidCursorError."""
        page, next_page, prev_page = self._fetch(self._rides.list_booked, id_user, scope, page_size, cursor)
        items = [
            MyBookingItem(
                id_booking=str(r["id_booking"]),
                status=r["booking_status"],
                seats_booked=r["seats_booked"],
                price_per_seat=_money(r["booking_price_per_seat"]),
                total_amount=_money(r["total_amount"]),
                rider_note=r["rider_note"],
                created_at=_utc(r["booking_created_at"]),
                ride=RideInfo(**_ride_fields(r)),
            )
            for r in page
        ]
        return MyBookingsResponse(items=items, next_page=next_page, prev_page=prev_page)
