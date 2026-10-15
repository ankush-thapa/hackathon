from datetime import datetime, timezone
from decimal import Decimal

from app.core.pagination import as_datetime, decode_cursor, paginate
from app.repositories.my_ride_repo import MyRideRepository
from app.schemas.my_ride import (
    DriverInfo,
    MyBookingItem,
    MyBookingsResponse,
    MyRideItem,
    MyRidesResponse,
    MyRideScope,
    RideInfo,
    RideRequestsInfo,
    StationInfo,
    VehicleInfo,
)


def _utc(v) -> datetime | None:
    return as_datetime(v).replace(tzinfo=timezone.utc) if v else None


def _money(v) -> Decimal:
    return Decimal(str(v)).quantize(Decimal("0.01"))


def _ride_fields(r: dict) -> dict:
    return dict(
        id_ride=str(r["id_ride"]),
        status=r["ride_status"],
        source=StationInfo(id_station=r["id_source_station"], name=r["source_station_name"]),
        destination=StationInfo(id_station=r["id_destination_station"], name=r["destination_station_name"]),
        departure_time=_utc(r["departure_time"]),
        estimated_arrival_time=_utc(r["estimated_arrival_time"]),
        total_seats=r["total_seats"],
        available_seats=r["available_seats"],
        price_per_seat=_money(r["price_per_seat"]),
        notes=r["notes"],
        driver=DriverInfo(id_user=str(r["id_driver"]), full_name=r["driver_name"], photo_url=r["driver_photo_url"]),
        vehicle=VehicleInfo(
            make=r["vehicle_make"], model=r["vehicle_model"], color=r["vehicle_color"], vehicle_type=r["vehicle_type"]
        )
        if r["vehicle_make"]
        else None,
    )


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
