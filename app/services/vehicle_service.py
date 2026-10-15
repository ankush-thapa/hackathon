<<<<<<< Updated upstream
from app.core.ids import new_id
from app.repositories.vehicle_repo import VehicleRepository
from app.schemas.vehicle import AddVehicleRequest, VehicleResponse


class VehicleService:
    def __init__(self, vehicles: VehicleRepository):
        self._vehicles = vehicles

    def add(self, id_user: int, req: AddVehicleRequest) -> VehicleResponse:
        # Raises DuplicateRegistrationError. The user's first active vehicle becomes their default.
        id_vehicle = new_id()
        is_default = not self._vehicles.has_active_vehicle(id_user)
        self._vehicles.create(
            {
                "id_vehicle": id_vehicle,
                "id_user": id_user,
                "make": req.make,
                "model": req.model,
                "color": req.colour,
                "registration_number": req.registration_number,
                "seat_capacity": req.seat_capacity,
                "vehicle_type": req.vehicle_type,
                "car_photo": req.photo_url,
                "is_default": is_default,
            }
        )
        return VehicleResponse(
            id=str(id_vehicle),
            photo_url=req.photo_url,
            make=req.make,
            model=req.model,
            registration_number=req.registration_number,
            colour=req.colour,
            seat_capacity=req.seat_capacity,
            vehicle_type=req.vehicle_type,
            is_default=is_default,
            status="active",
        )
=======
from datetime import datetime, timezone

from app.core.ids import new_id
from app.repositories.vehicle_repo import VehicleRepository, VehicleRow
from app.schemas.vehicle import VehicleCreate, VehicleStatus, VehicleUpdate


class VehicleNotFoundError(Exception):
    pass


class InactiveDefaultError(Exception):
    """An inactive vehicle cannot be the default."""


# API field -> column
_COLUMNS = {
    "make": "make",
    "model": "model",
    "color": "color",
    "registrationNumber": "registration_number",
    "seatCapacity": "seat_capacity",
    "vehicleType": "vehicle_type",
    "isDefault": "is_default",
    "status": "status",
}


def _utcnow() -> datetime:
    # Naive UTC: DATETIME(3) columns carry no zone.
    return datetime.now(timezone.utc).replace(tzinfo=None)


class VehicleService:
    """A user's vehicles. Each user has at most one default vehicle, and it is always active."""

    def __init__(self, vehicles: VehicleRepository):
        self._vehicles = vehicles

    def create(self, id_user: int, req: VehicleCreate) -> VehicleRow:
        # Raises DuplicateRegistrationError.
        id_vehicle = new_id()
        self._vehicles.create(
            id_user,
            id_vehicle,
            {
                "make": req.make,
                "model": req.model,
                "color": req.color,
                "registration_number": req.registrationNumber,
                "seat_capacity": req.seatCapacity,
                "vehicle_type": req.vehicleType.value,
                "is_default": req.isDefault or not self._vehicles.has_any(id_user),
            },
            _utcnow(),
        )
        return self._vehicles.get(id_user, id_vehicle)

    def list(self, id_user: int, status: VehicleStatus | None) -> list[VehicleRow]:
        return self._vehicles.list(id_user, status.value if status else None)

    def get(self, id_user: int, id_vehicle: int) -> VehicleRow:
        vehicle = self._vehicles.get(id_user, id_vehicle)
        if vehicle is None:
            raise VehicleNotFoundError
        return vehicle

    def update(self, id_user: int, id_vehicle: int, req: VehicleUpdate) -> VehicleRow:
        # Raises VehicleNotFoundError, InactiveDefaultError, DuplicateRegistrationError.
        current = self.get(id_user, id_vehicle)
        changes = {
            _COLUMNS[field]: value.value if hasattr(value, "value") else value
            for field, value in req.model_dump(exclude_unset=True).items()
        }
        status = changes.get("status", current.status)
        if status == VehicleStatus.inactive.value:
            if changes.get("is_default"):
                raise InactiveDefaultError
            changes["is_default"] = False  # deactivating the default leaves the user without one
        self._vehicles.update(id_user, id_vehicle, changes, _utcnow())
        return self.get(id_user, id_vehicle)

    def delete(self, id_user: int, id_vehicle: int) -> None:
        if not self._vehicles.soft_delete(id_user, id_vehicle, _utcnow()):
            raise VehicleNotFoundError
>>>>>>> Stashed changes
