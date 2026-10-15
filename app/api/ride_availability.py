from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.models.ride import Ride, RideStatus

router = APIRouter(tags=["rides"])


def reject_boolean(value):
    if isinstance(value, bool): raise ValueError("ride ID must be a positive integer")
    return value


RideId = Annotated[int, Field(gt=0, le=2**64-1), BeforeValidator(reject_boolean)]


class AvailabilityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id_rides: list[RideId] = Field(min_length=1, max_length=100, description="IDs from loaded search results; large IDs may be strings.")
    seats: int = Field(default=1, ge=1, le=8, strict=True)


class AvailabilityItem(BaseModel):
    idRide: str
    availableSeats: int


class AvailabilityResponse(BaseModel):
    items: list[AvailabilityItem]


@router.post("/v1/rides/availability", response_model=AvailabilityResponse)
def availability(request: AvailabilityRequest, response: Response,
                 user: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    """Refresh loaded search results. Missing IDs are no longer bookable and should be removed.

    Body: id_rides (1-100 IDs) and optional seats (default 1). This read never reserves seats.
    """
    response.headers["Cache-Control"] = "no-store"
    rows = db.execute(select(Ride.id_ride, Ride.available_seats).where(
        Ride.id_ride.in_(request.id_rides), Ride.id_driver != user,
        Ride.status == RideStatus.open, Ride.available_seats >= request.seats,
        Ride.departure_time > datetime.now(timezone.utc).replace(tzinfo=None),
    )).all()
    return AvailabilityResponse(items=[AvailabilityItem(idRide=str(r.id_ride), availableSeats=r.available_seats) for r in rows])
