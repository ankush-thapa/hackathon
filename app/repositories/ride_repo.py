from sqlalchemy import Numeric, bindparam, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.types import DateTime3, UnsignedBigInt, UnsignedInt, UnsignedTinyInt


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
    "SELECT id_station, is_active FROM station "
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


class RideRepository:
    """Validate referenced rows and create the offer in one database transaction."""

    def __init__(self, db: Session):
        self._db = db

    def create(self, params: dict) -> dict:
        # Lock reference rows on MySQL so ownership, status, and capacity stay
        # valid until the offer is committed. SQLite is used by the API tests.
        lock = " FOR UPDATE" if self._db.get_bind().dialect.name == "mysql" else ""
        try:
            vehicle = self._db.execute(text(_VEHICLE_SQL + lock), params).first()
            if vehicle is None:
                raise VehicleNotFoundError
            if vehicle.status != "active":
                raise VehicleInactiveError
            if params["total_seats"] > vehicle.seat_capacity:
                raise VehicleCapacityError
            stations = {
                row.id_station: row.is_active
                for row in self._db.execute(text(_STATIONS_SQL + lock), params)
            }
            for field in ("id_source_station", "id_destination_station"):
                if not stations.get(params[field]):
                    raise StationNotFoundError(field)
            self._db.execute(_INSERT_RIDE, params)
            ride = dict(self._db.execute(_SELECT_RIDE, {"id_ride": params["id_ride"]}).mappings().one())
            self._db.commit()
            return ride
        except IntegrityError as error:
            self._db.rollback()
            raise RideConflictError from error
        except Exception:
            self._db.rollback()
            raise
