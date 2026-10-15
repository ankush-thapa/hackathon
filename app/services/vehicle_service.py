from datetime import datetime, timezone

from app.core.ids import new_id
from app.repositories.vehicle_repo import VehicleRepository, VehicleRow
from app.schemas.vehicle import AddVehicleRequest, AddVehicleResponse, VehicleCreate, VehicleStatus, VehicleUpdate


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
    "photoUrl": "car_photo",
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
                "is_default": req.isDefault or not self._vehicles.has_active_vehicle(id_user),
                "car_photo": req.photoUrl,
            },
            _utcnow(),
        )
        return self._vehicles.get(id_user, id_vehicle)

    def add(self, id_user: int, req: AddVehicleRequest) -> AddVehicleResponse:
        vehicle = self.create(id_user, VehicleCreate(
            make=req.make, model=req.model, color=req.colour,
            registrationNumber=req.registration_number, seatCapacity=req.seat_capacity,
            vehicleType=req.vehicle_type, photoUrl=req.photo_url,
        ))
        return AddVehicleResponse(
            id=str(vehicle.id_vehicle), photo_url=vehicle.car_photo,
            make=vehicle.make, model=vehicle.model, registration_number=vehicle.registration_number,
            colour=vehicle.color, seat_capacity=vehicle.seat_capacity,
            vehicle_type=vehicle.vehicle_type, is_default=vehicle.is_default, status=vehicle.status,
        )

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
