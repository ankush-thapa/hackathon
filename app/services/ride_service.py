from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from app.core.idempotency import creation_id
from app.core.pagination import InvalidCursorError, as_datetime, decode_cursor, paginate  # noqa: F401
from app.repositories.ride_repo import RideRepository, StationNotFoundError
from app.schemas.ride import (
    DriverSummary,
    OfferRideRequest,
    RideListResponse,
    RideSummary,
    StationRef,
    VehicleSummary,
)


class DepartureInPastError(Exception):
    pass


class RideService:
    def __init__(self, rides: RideRepository):
        self._rides = rides

    def offer(self, driver_id: int, request: OfferRideRequest, idempotency_key: str | None = None) -> dict:
        if not idempotency_key and request.departure_time <= datetime.now(timezone.utc):
            raise DepartureInPastError
        params = request.model_dump()
        params.update(id_ride=creation_id(driver_id, "offer", idempotency_key), id_driver=driver_id)
        # DATETIME(3) stores naive UTC, while the public API requires timezones.
        for field in ("departure_time", "estimated_arrival_time"):
            if params[field] is not None:
                params[field] = params[field].replace(tzinfo=None)
        return self._rides.create(params)

    def search(
        self,
        *,
        id_source_station: int,
        id_destination_station: int,
        departure_date: date,
        seats: int,
        exclude_driver_id: int,
        page_size: int,
        cursor: str | None,
    ) -> RideListResponse:
        """Open rides between two stations departing on `departure_date` (UTC day) with enough free seats,
        excluding rides offered by `exclude_driver_id` (the caller).

        Raises StationNotFoundError / InvalidCursorError.
        """
        for field, station_id in (("idSourceStation", id_source_station), ("idDestinationStation", id_destination_station)):
            if not self._rides.station_exists(station_id):
                raise StationNotFoundError(field)
        direction, position = None, None
        if cursor:
            direction, *position = decode_cursor(cursor)
            position = tuple(position)

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        day_start = datetime.combine(departure_date, time.min)
        rows = self._rides.search_open(
            id_source_station=id_source_station,
            id_destination_station=id_destination_station,
            seats=seats,
            exclude_driver_id=exclude_driver_id,
            departure_from=max(day_start, now),  # never list rides that already left
            departure_until=day_start + timedelta(days=1),
            after=position if direction == "n" else None,
            before=position if direction == "p" else None,
            limit=page_size + 1,  # one extra row tells us whether another page exists
        )
        page, next_page, prev_page = paginate(rows, page_size, direction, lambda r: (r["departure_time"], r["id_ride"]))
        return RideListResponse(items=[self._to_summary(r) for r in page], next_page=next_page, prev_page=prev_page)

    @staticmethod
    def _to_summary(r: dict) -> RideSummary:
        return RideSummary(
            idRide=str(r["id_ride"]),
            source=StationRef(idStation=r["id_source_station"], name=r["source_station_name"]),
            destination=StationRef(idStation=r["id_destination_station"], name=r["destination_station_name"]),
            departureTime=as_datetime(r["departure_time"]).replace(tzinfo=timezone.utc),
            estimatedArrivalTime=as_datetime(r["estimated_arrival_time"]).replace(tzinfo=timezone.utc)
            if r["estimated_arrival_time"]
            else None,
            totalSeats=r["total_seats"],
            availableSeats=r["available_seats"],
            pricePerSeat=Decimal(str(r["price_per_seat"])).quantize(Decimal("0.01")),
            notes=r["notes"],
            driver=DriverSummary(
                userId=str(r["id_driver"]), fullName=r["driver_name"], photoUrl=r["driver_photo_url"]
            ),
            vehicle=VehicleSummary(
                make=r["vehicle_make"],
                model=r["vehicle_model"],
                color=r["vehicle_color"],
                vehicleType=r["vehicle_type"],
            )
            if r["vehicle_make"]
            else None,
        )
