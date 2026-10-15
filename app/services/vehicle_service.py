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
