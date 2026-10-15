from datetime import datetime, timezone

from app.core.ids import new_id
from app.repositories.ride_repo import RideRepository
from app.schemas.ride import OfferRideRequest


class DepartureInPastError(Exception):
    pass


class RideService:
    def __init__(self, rides: RideRepository):
        self._rides = rides

    def offer(self, driver_id: int, request: OfferRideRequest) -> dict:
        if request.departure_time <= datetime.now(timezone.utc):
            raise DepartureInPastError
        params = request.model_dump()
        params.update(id_ride=new_id(), id_driver=driver_id)
        # DATETIME(3) stores naive UTC, while the public API requires timezones.
        for field in ("departure_time", "estimated_arrival_time"):
            if params[field] is not None:
                params[field] = params[field].replace(tzinfo=None)
        return self._rides.create(params)
