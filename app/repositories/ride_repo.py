from app.core.transactions import retry_lock_conflicts
from datetime import datetime
from typing import Callable

from sqlalchemy import Numeric, bindparam, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.types import DateTime3, UnsignedBigInt, UnsignedInt, UnsignedTinyInt
from app.repositories.ride_schedule import lock_driver, ensure_departure_gap


class VehicleNotFoundError(Exception):
    pass


class VehicleInactiveError(Exception):
    pass


class VehicleCapacityError(Exception):
    pass


class StationNotFoundError(Exception):
    def __init__(self, field: str):
        self.field = field
        super().__init__(f"{field} is missing or inactive")


class RideConflictError(Exception):
    pass


_VEHICLE_SQL = (
    "SELECT id_vehicle, seat_capacity, status FROM vehicle "
    "WHERE id_vehicle = :id_vehicle AND id_user = :id_driver"
)
_STATIONS_SQL = (
    "SELECT id_station, station_name, is_active FROM station "
    "WHERE id_station IN (:id_source_station, :id_destination_station) ORDER BY id_station"
)
_INSERT_RIDE = text(
    "INSERT INTO ride (id_ride, id_driver, id_vehicle, id_source_station, id_destination_station, "
    "departure_time, estimated_arrival_time, total_seats, available_seats, price_per_seat, notes, status, version) "
    "VALUES (:id_ride, :id_driver, :id_vehicle, :id_source_station, :id_destination_station, "
    ":departure_time, :estimated_arrival_time, :total_seats, :total_seats, :price_per_seat, :notes, 'open', 1)"
).bindparams(
    bindparam("departure_time", type_=DateTime3),
    bindparam("estimated_arrival_time", type_=DateTime3),
    bindparam("price_per_seat", type_=Numeric(10, 2)),
)
_SELECT_RIDE = text(
    "SELECT id_ride, id_driver, id_vehicle, id_source_station, id_destination_station, "
    "departure_time, estimated_arrival_time, total_seats, available_seats, price_per_seat, "
    "notes, status, version, created_at, updated_at FROM ride WHERE id_ride = :id_ride"
).columns(
    id_ride=UnsignedBigInt, id_driver=UnsignedBigInt, id_vehicle=UnsignedBigInt,
    id_source_station=UnsignedInt, id_destination_station=UnsignedInt,
    departure_time=DateTime3, estimated_arrival_time=DateTime3,
    total_seats=UnsignedTinyInt, available_seats=UnsignedTinyInt,
    price_per_seat=Numeric(10, 2), created_at=DateTime3, updated_at=DateTime3,
)

_STATION_EXISTS = text("SELECT 1 FROM station WHERE id_station = :id AND is_active = 1 LIMIT 1")

# Fixed fragments only: every user-supplied value is a bound parameter.
_SEARCH_SELECT = """
SELECT r.id_ride, r.id_driver,
       r.id_source_station, ss.station_name AS source_station_name,
       r.id_destination_station, ds.station_name AS destination_station_name,
       r.departure_time, r.estimated_arrival_time, r.total_seats, r.available_seats,
       r.price_per_seat, r.notes,
       p.full_name AS driver_name, p.photo_url AS driver_photo_url,
       v.make AS vehicle_make, v.model AS vehicle_model, v.color AS vehicle_color,
       v.vehicle_type AS vehicle_type
FROM ride r
JOIN station ss ON ss.id_station = r.id_source_station
JOIN station ds ON ds.id_station = r.id_destination_station
LEFT JOIN user_profile p ON p.id_user = r.id_driver
LEFT JOIN vehicle v ON v.id_vehicle = r.id_vehicle
WHERE r.id_source_station = :id_source_station
  AND r.id_destination_station = :id_destination_station
  AND r.status = 'open'
  AND r.available_seats >= :seats
  AND r.departure_time >= :departure_from
  AND r.departure_time < :departure_until
  AND r.id_driver <> :exclude_driver
"""
_AFTER_CURSOR = "  AND (r.departure_time > :cursor_time OR (r.departure_time = :cursor_time AND r.id_ride > :cursor_id))\n"
_BEFORE_CURSOR = "  AND (r.departure_time < :cursor_time OR (r.departure_time = :cursor_time AND r.id_ride < :cursor_id))\n"
_ORDER_ASC = "ORDER BY r.departure_time, r.id_ride\nLIMIT :limit"
_ORDER_DESC = "ORDER BY r.departure_time DESC, r.id_ride DESC\nLIMIT :limit"


class RideRepository:
    """Plain-SQL access to `ride`: create an offer transactionally, and search open rides."""

    def __init__(self, db: Session):
        self._db = db

    @retry_lock_conflicts
    def create(self, params: dict, emit: Callable[[dict], None] | None = None) -> dict:
        # Lock reference rows on MySQL so ownership, status, and capacity stay
        # valid until the offer is committed. SQLite is used by the API tests.
        lock = " FOR UPDATE" if self._db.get_bind().dialect.name == "mysql" else ""
        try:
            lock_driver(self._db, params["id_driver"])
            vehicle = self._db.execute(text(_VEHICLE_SQL + lock), params).first()
            if vehicle is None:
                raise VehicleNotFoundError
            if vehicle.status != "active":
                raise VehicleInactiveError
            if params["total_seats"] > vehicle.seat_capacity:
                raise VehicleCapacityError
            station_rows = list(self._db.execute(text(_STATIONS_SQL + (" FOR SHARE" if lock else "")), params))
            stations = {row.id_station: row.is_active for row in station_rows}
            names = {row.id_station: row.station_name for row in station_rows}
            for field in ("id_source_station", "id_destination_station"):
                if not stations.get(params[field]):
                    raise StationNotFoundError(field)
            existing_query = text(_SELECT_RIDE.element.text + lock).columns(**{column.key: column.type for column in _SELECT_RIDE.selected_columns})
            existing = self._db.execute(existing_query, {"id_ride": params["id_ride"]}).mappings().first()
            if existing:
                fields = ("id_driver", "id_vehicle", "id_source_station", "id_destination_station", "departure_time",
                          "estimated_arrival_time", "total_seats", "price_per_seat", "notes")
                if any(existing[k] != params[k] for k in fields):
                    from fastapi import HTTPException
                    raise HTTPException(409, "Idempotency-Key already used for a different or modified ride")
                self._db.commit()
                return dict(existing)
            from datetime import datetime, timezone
            if params["departure_time"] <= datetime.now(timezone.utc).replace(tzinfo=None):
                from app.services.ride_service import DepartureInPastError
                raise DepartureInPastError
            ensure_departure_gap(self._db, params["id_driver"], params["departure_time"], params["id_ride"])
            self._db.execute(_INSERT_RIDE, params)
            ride = dict(self._db.execute(_SELECT_RIDE, {"id_ride": params["id_ride"]}).mappings().one())
            if emit is not None:  # inside the open transaction: the notification commits or rolls back with the ride
                emit({
                    "event": "ride_created", "id_ride": ride["id_ride"], "id_driver": params["id_driver"],
                    "seats": params["total_seats"], "departure_time": ride["departure_time"],
                    "route": f"{names[params['id_source_station']]} → {names[params['id_destination_station']]}",
                })
            self._db.commit()
            return ride
        except IntegrityError as error:
            self._db.rollback()
            raise RideConflictError from error
        except Exception:
            self._db.rollback()
            raise

    def station_exists(self, id_station: int) -> bool:
        return self._db.execute(_STATION_EXISTS, {"id": id_station}).first() is not None

    def search_open(
        self,
        *,
        id_source_station: int,
        id_destination_station: int,
        seats: int,
        exclude_driver_id: int,
        departure_from: datetime,
        departure_until: datetime,
        after: tuple[datetime, int] | None,
        before: tuple[datetime, int] | None,
        limit: int,
    ) -> list[dict]:
        """Rows in departure order. `before` pages backwards (rows come back nearest-first, so callers reverse them)."""
        sql = _SEARCH_SELECT
        params: dict = {
            "id_source_station": id_source_station,
            "id_destination_station": id_destination_station,
            "seats": seats,
            "exclude_driver": exclude_driver_id,  # a driver never sees their own rides in search
            "departure_from": departure_from,  # inclusive
            "departure_until": departure_until,  # exclusive
            "limit": limit,
        }
        if after is not None:
            sql += _AFTER_CURSOR
            params["cursor_time"], params["cursor_id"] = after
        elif before is not None:
            sql += _BEFORE_CURSOR
            params["cursor_time"], params["cursor_id"] = before
        order = _ORDER_DESC if before is not None else _ORDER_ASC
        rows = self._db.execute(text(sql + order), params).mappings().all()
        return [dict(r) for r in rows]
