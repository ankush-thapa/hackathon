from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import DateTime, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


class DuplicateRegistrationError(Exception):
    pass


@dataclass(frozen=True)
class VehicleRow:
    id_vehicle: int
    make: str
    model: str
    color: str
    registration_number: str
    seat_capacity: int
    vehicle_type: str
    is_default: bool
    status: str
    created_at: datetime
    updated_at: datetime
    car_photo: str | None = None


_COLUMNS = (
    "id_vehicle, make, model, color, registration_number, seat_capacity, vehicle_type, "
    "is_default, status, created_at, updated_at, car_photo"
)
# Typed so SQLite returns datetimes, not strings.
_GET = text(
    f"SELECT {_COLUMNS} FROM vehicle WHERE id_vehicle = :id_vehicle AND id_user = :id_user AND status <> 'deleted'"
).columns(created_at=DateTime, updated_at=DateTime)
_LIST = text(
    f"SELECT {_COLUMNS} FROM vehicle WHERE id_user = :id_user AND status <> 'deleted' "
    "AND (:status IS NULL OR status = :status) ORDER BY is_default DESC, created_at DESC, id_vehicle DESC"
).columns(created_at=DateTime, updated_at=DateTime)
_HAS_ANY = text("SELECT 1 FROM vehicle WHERE id_user = :id_user AND status <> 'deleted' LIMIT 1")
_HAS_ACTIVE = text("SELECT 1 FROM vehicle WHERE id_user = :id_user AND status = 'active' LIMIT 1")
_REGISTRATION_EXISTS = text("SELECT 1 FROM vehicle WHERE registration_number = :registration_number LIMIT 1")
_INSERT = text(
    "INSERT INTO vehicle (id_vehicle, id_user, make, model, color, registration_number, seat_capacity, "
    "vehicle_type, car_photo, is_default, status, created_at, updated_at) VALUES (:id_vehicle, :id_user, :make, :model, "
    ":color, :registration_number, :seat_capacity, :vehicle_type, :car_photo, :is_default, 'active', :now, :now)"
)
_CLEAR_DEFAULT = text(
    "UPDATE vehicle SET is_default = 0, updated_at = :now "
    "WHERE id_user = :id_user AND is_default = 1 AND id_vehicle <> :keep"
)
# A soft-deleted vehicle still holds its registration number under the unique key; free it for reuse.
_PURGE_DELETED_REGISTRATION = text(
    "DELETE FROM vehicle WHERE registration_number = :registration_number AND status = 'deleted'"
)
_SOFT_DELETE = text(
    "UPDATE vehicle SET status = 'deleted', is_default = 0, updated_at = :now "
    "WHERE id_vehicle = :id_vehicle AND id_user = :id_user AND status <> 'deleted'"
)
_UPDATABLE = ("make", "model", "color", "registration_number", "seat_capacity", "vehicle_type", "is_default", "status", "car_photo")


class VehicleRepository:
    """Plain-SQL access to the `vehicle` table, always scoped to one owner. Datetimes are naive UTC."""

    def __init__(self, db: Session):
        self._db = db

    def get(self, id_user: int, id_vehicle: int) -> VehicleRow | None:
        row = self._db.execute(_GET, {"id_user": id_user, "id_vehicle": id_vehicle}).first()
        return _to_row(row) if row else None

    def list(self, id_user: int, status: str | None) -> list[VehicleRow]:
        return [_to_row(r) for r in self._db.execute(_LIST, {"id_user": id_user, "status": status})]

    def has_any(self, id_user: int) -> bool:
        return self._db.execute(_HAS_ANY, {"id_user": id_user}).first() is not None

    def has_active_vehicle(self, id_user: int) -> bool:
        return self._db.execute(_HAS_ACTIVE, {"id_user": id_user}).first() is not None

    def create(self, id_user: int, id_vehicle: int, values: dict, now: datetime) -> None:
        """Insert an active vehicle. Raises DuplicateRegistrationError if another live vehicle has the number."""
        try:
            self._db.execute(_PURGE_DELETED_REGISTRATION, {"registration_number": values["registration_number"]})
            if values["is_default"]:
                self._db.execute(_CLEAR_DEFAULT, {"id_user": id_user, "keep": id_vehicle, "now": now})
            self._db.execute(_INSERT, {**values, "id_vehicle": id_vehicle, "id_user": id_user, "now": now})
            self._db.commit()  # unique key is the source of truth, so this is race-safe
        except IntegrityError:
            self._db.rollback()
            if "registration_number" in values and self._db.execute(
                _REGISTRATION_EXISTS, {"registration_number": values["registration_number"]}
            ).first():
                raise DuplicateRegistrationError from None
            raise

    def update(self, id_user: int, id_vehicle: int, changes: dict, now: datetime) -> None:
        """Apply column changes (keys from _UPDATABLE). Raises DuplicateRegistrationError on a number clash."""
        unknown = set(changes) - set(_UPDATABLE)
        if unknown:
            raise ValueError(f"not updatable: {sorted(unknown)}")
        assignments = ", ".join(f"{column} = :{column}" for column in changes)
        statement = text(
            f"UPDATE vehicle SET {assignments}, updated_at = :now "
            "WHERE id_vehicle = :id_vehicle AND id_user = :id_user AND status <> 'deleted'"
        )
        try:
            if "registration_number" in changes:
                self._db.execute(_PURGE_DELETED_REGISTRATION, {"registration_number": changes["registration_number"]})
            if changes.get("is_default"):
                self._db.execute(_CLEAR_DEFAULT, {"id_user": id_user, "keep": id_vehicle, "now": now})
            self._db.execute(statement, {**changes, "id_vehicle": id_vehicle, "id_user": id_user, "now": now})
            self._db.commit()
        except IntegrityError:
            self._db.rollback()
            if "registration_number" in changes and self._db.execute(
                _REGISTRATION_EXISTS, {"registration_number": changes["registration_number"]}
            ).first():
                raise DuplicateRegistrationError from None
            raise

    def soft_delete(self, id_user: int, id_vehicle: int, now: datetime) -> bool:
        deleted = self._db.execute(_SOFT_DELETE, {"id_user": id_user, "id_vehicle": id_vehicle, "now": now}).rowcount
        self._db.commit()
        return deleted == 1


def _to_row(r) -> VehicleRow:
    return VehicleRow(
        r.id_vehicle, r.make, r.model, r.color, r.registration_number, r.seat_capacity, r.vehicle_type,
        bool(r.is_default), r.status, r.created_at, r.updated_at, r.car_photo,
    )
