from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id, require_session
from app.db.session import get_db
from app.repositories.ride_repo import (
    RideConflictError,
    RideRepository,
    StationNotFoundError,
    VehicleCapacityError,
    VehicleInactiveError,
    VehicleNotFoundError,
)
from app.schemas.ride import OfferRideRequest, OfferRideResponse, RideListResponse
from app.services.ride_service import DepartureInPastError, InvalidCursorError, RideService

router = APIRouter(prefix="/v1/rides", tags=["rides"])


def get_ride_service(db: Session = Depends(get_db)) -> RideService:
    return RideService(RideRepository(db))


@router.post(
    "/offer", response_model=OfferRideResponse, status_code=status.HTTP_201_CREATED,
    summary="Offer a ride",
    responses={
        401: {"description": "Missing, invalid, expired, or revoked access token"},
        404: {"description": "Vehicle not owned by the driver, or station missing/inactive"},
        409: {"description": "Referenced data changed; retry the request"},
        422: {"description": "Invalid route, times, seats, price, or inactive vehicle"},
    },
)
def offer_ride(
    request: OfferRideRequest,
    current_user_id: int = Depends(get_current_user_id),
    service: RideService = Depends(get_ride_service),
):
    """Create an offer using Authorization: Bearer <accessToken>.

    id_vehicle is required and must belong to the logged-in driver. The server
    sets id_driver, available_seats = total_seats, status = open, and version = 1.
    Send timezone-aware times; responses are UTC and large IDs are strings.
    """
    try:
        ride = service.offer(current_user_id, request)
    except VehicleNotFoundError:
        raise HTTPException(404, detail="vehicle not found for this driver") from None
    except StationNotFoundError as error:
        raise HTTPException(404, detail=f"{error.field} not found or inactive") from None
    except VehicleInactiveError:
        raise HTTPException(422, detail="vehicle must be active") from None
    except VehicleCapacityError:
        raise HTTPException(422, detail="total_seats exceeds vehicle seat capacity") from None
    except DepartureInPastError:
        raise HTTPException(422, detail="departure_time must be in the future") from None
    except RideConflictError:
        raise HTTPException(409, detail="ride could not be created; retry the request") from None
    return OfferRideResponse.model_validate(ride)


@router.get(
    "",
    response_model=RideListResponse,
    responses={401: {"description": "Missing or invalid session"}, 404: {"description": "Unknown station"}},
)
@require_session
def list_rides(
    idSourceStation: Annotated[int, Query(gt=0)],
    idDestinationStation: Annotated[int, Query(gt=0)],
    departureDate: Annotated[
        date, Query(description="Day to travel (YYYY-MM-DD), taken as a UTC calendar day. Rides that already left are not listed.")
    ],
    seats: Annotated[int, Query(ge=1, le=8, description="Minimum free seats.")] = 1,
    pageSize: Annotated[int, Query(ge=1, le=50, description="Rides per page.")] = 20,
    cursor: Annotated[str | None, Query(description="`next_page` or `prev_page` from a previous response.")] = None,
    service: RideService = Depends(get_ride_service),
):
    """Open rides between two stations, soonest first, with at least `seats` seats free."""
    if idSourceStation == idDestinationStation:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="source and destination must differ")
    try:
        return service.search(
            id_source_station=idSourceStation,
            id_destination_station=idDestinationStation,
            departure_date=departureDate,
            seats=seats,
            page_size=pageSize,
            cursor=cursor,
        )
    except StationNotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"{e.field}: station not found")
    except InvalidCursorError:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid cursor")
