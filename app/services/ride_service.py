import base64
from decimal import Decimal
from datetime import date, datetime, time, timedelta, timezone

from app.repositories.ride_repo import RideRepository
from app.schemas.ride import (
    DriverSummary,
    RideListResponse,
    RideSummary,
    StationRef,
    VehicleSummary,
)


class StationNotFoundError(Exception):
    def __init__(self, field: str):
        self.field = field


class InvalidCursorError(Exception):
    pass


def _as_datetime(v: datetime | str) -> datetime:
    """MySQL returns datetime objects; SQLite (tests) returns ISO strings for raw queries."""
    return datetime.fromisoformat(v) if isinstance(v, str) else v


def _encode_cursor(direction: str, departure_time: datetime, id_ride: int) -> str:
    """direction: 'n' = rows after this position, 'p' = rows before it."""
    return base64.urlsafe_b64encode(f"{direction}|{departure_time.isoformat()}|{id_ride}".encode()).decode()


def _decode_cursor(cursor: str) -> tuple[str, datetime, int]:
    try:
        direction, time_part, id_part = base64.urlsafe_b64decode(cursor.encode()).decode().split("|")
        if direction not in ("n", "p"):
            raise ValueError
        return direction, datetime.fromisoformat(time_part), int(id_part)
    except (ValueError, UnicodeDecodeError):
        raise InvalidCursorError from None


class RideService:
    def __init__(self, rides: RideRepository):
        self._rides = rides

    def search(
        self,
        *,
        id_source_station: int,
        id_destination_station: int,
        departure_date: date,
        seats: int,
        page_size: int,
        cursor: str | None,
    ) -> RideListResponse:
        """Open rides between two stations departing on `departure_date` (UTC day) with enough free seats.

        Raises StationNotFoundError / InvalidCursorError.
        """
        for field, station_id in (("idSourceStation", id_source_station), ("idDestinationStation", id_destination_station)):
            if not self._rides.station_exists(station_id):
                raise StationNotFoundError(field)
        direction, position = (None, None)
        if cursor:
            direction, *position = _decode_cursor(cursor)
            position = tuple(position)
        going_back = direction == "p"

        now = datetime.now(timezone.utc).replace(tzinfo=None)
        day_start = datetime.combine(departure_date, time.min)
        rows = self._rides.search_open(
            id_source_station=id_source_station,
            id_destination_station=id_destination_station,
            seats=seats,
            departure_from=max(day_start, now),  # never list rides that already left
            departure_until=day_start + timedelta(days=1),
            after=position if direction == "n" else None,
            before=position if going_back else None,
            limit=page_size + 1,  # one extra row tells us whether another page exists
        )
        page, has_more = rows[:page_size], len(rows) > page_size
        if going_back:
            page.reverse()  # fetched nearest-first; present in departure order
        if not page:
            return RideListResponse(items=[], next_page=None, prev_page=None)

        def token(d: str, row: dict) -> str:
            return _encode_cursor(d, _as_datetime(row["departure_time"]), row["id_ride"])

        # Moving in a direction means we came from the other side, so that link always exists.
        has_next = has_more if direction != "p" else True
        has_prev = has_more if going_back else direction == "n"
        return RideListResponse(
            items=[self._to_summary(r) for r in page],
            next_page=token("n", page[-1]) if has_next else None,
            prev_page=token("p", page[0]) if has_prev else None,
        )

    @staticmethod
    def _to_summary(r: dict) -> RideSummary:
        return RideSummary(
            idRide=str(r["id_ride"]),
            source=StationRef(idStation=r["id_source_station"], name=r["source_station_name"]),
            destination=StationRef(idStation=r["id_destination_station"], name=r["destination_station_name"]),
            departureTime=_as_datetime(r["departure_time"]).replace(tzinfo=timezone.utc),
            estimatedArrivalTime=_as_datetime(r["estimated_arrival_time"]).replace(tzinfo=timezone.utc)
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
