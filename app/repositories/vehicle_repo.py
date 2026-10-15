from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session


class DuplicateRegistrationError(Exception):
    pass


_HAS_ACTIVE_VEHICLE = text(
    "SELECT 1 FROM vehicle WHERE id_user = :id_user AND status = 'active' LIMIT 1"
)
_REGISTRATION_EXISTS = text("SELECT 1 FROM vehicle WHERE registration_number = :registration_number LIMIT 1")
_INSERT_VEHICLE = text(
    "INSERT INTO vehicle (id_vehicle, id_user, make, model, color, registration_number, seat_capacity, "
    "vehicle_type, car_photo, is_default, status) "
    "VALUES (:id_vehicle, :id_user, :make, :model, :color, :registration_number, :seat_capacity, "
    ":vehicle_type, :car_photo, :is_default, 'active')"
)


class VehicleRepository:
    """Plain-SQL access to the `vehicle` table (no ORM)."""

    def __init__(self, db: Session):
        self._db = db

    def has_active_vehicle(self, id_user: int) -> bool:
        return self._db.execute(_HAS_ACTIVE_VEHICLE, {"id_user": id_user}).first() is not None

    def create(self, params: dict) -> None:
        """Insert a vehicle. Raises DuplicateRegistrationError if the registration number is taken."""
        try:
            self._db.execute(_INSERT_VEHICLE, params)
            self._db.commit()  # uk_vehicle_registration_number is the source of truth, so this is race-safe
        except IntegrityError:
            self._db.rollback()
            if self._db.execute(_REGISTRATION_EXISTS, {"registration_number": params["registration_number"]}).first():
                raise DuplicateRegistrationError from None
            raise
