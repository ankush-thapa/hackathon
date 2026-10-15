from datetime import date, datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Header, Path, Query, status
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
from app.repositories.notification_repo import NotificationRepository
from app.repositories.ride_detail_repo import RideDetailRepository
from app.schemas.ride import OfferRideRequest, OfferRideResponse, RideListResponse
from app.schemas.ride_detail import RideDetailResponse
from app.services.notification_service import NotificationService
from app.services.ride_detail_service import RideDetailService, RideNotFoundError
from app.services.ride_service import DepartureInPastError, InvalidCursorError, RideService

router = APIRouter(prefix="/v1/rides", tags=["rides"])


def get_ride_service(db: Session = Depends(get_db)) -> RideService:
    return RideService(RideRepository(db), NotificationService(NotificationRepository(db)))


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
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", min_length=8, max_length=128),
    current_user_id: int = Depends(get_current_user_id),
    service: RideService = Depends(get_ride_service),
):
    """Create an offer using Authorization: Bearer <accessToken>.

    id_vehicle is required and must belong to the logged-in driver. The server
    sets id_driver, available_seats = total_seats, status = open, and version = 1.
    Send timezone-aware times; responses are UTC and large IDs are strings.
    Optional Idempotency-Key (8-128 chars): reuse it with identical payload for a safe retry.
    Replays return the current resource state; changed payload/resource fields return 409.
    """
    try:
        ride = service.offer(current_user_id, request, idempotency_key)
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
    responses={
        401: {"description": "Missing or invalid session"},
        404: {"description": "Unknown station"},
        422: {"description": "Invalid filters, a past departureDate, or a bad cursor"},
    },
)
@require_session
def list_rides(
    idSourceStation: Annotated[int, Query(gt=0)],
    idDestinationStation: Annotated[int, Query(gt=0)],
    departureDate: Annotated[
        date,
        Query(
            description="Day to travel (YYYY-MM-DD), taken as a UTC calendar day. Today or later; "
            "for today, rides that already left are not listed."
        ),
    ],
    seats: Annotated[int, Query(ge=1, le=8, description="Minimum free seats.")] = 1,
    pageSize: Annotated[int, Query(ge=1, le=50, description="Rides per page.")] = 20,
    cursor: Annotated[str | None, Query(description="`next_page` or `prev_page` from a previous response.")] = None,
    service: RideService = Depends(get_ride_service),
    *,
    current_user_id: int,
):
    """Open rides between two stations, soonest first, with at least `seats` seats free.

    Rides the logged-in user offered themselves are not listed (see GET /v1/me/rides for those).
    """
    if idSourceStation == idDestinationStation:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="source and destination must differ")
    if departureDate < datetime.now(timezone.utc).date():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="departureDate must not be in the past")
    try:
        return service.search(
            id_source_station=idSourceStation,
            id_destination_station=idDestinationStation,
            departure_date=departureDate,
            seats=seats,
            exclude_driver_id=current_user_id,
            page_size=pageSize,
            cursor=cursor,
        )
    except StationNotFoundError as e:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"{e.field}: station not found")
    except InvalidCursorError:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid cursor")


def get_ride_detail_service(db: Session = Depends(get_db)) -> RideDetailService:
    return RideDetailService(RideDetailRepository(db))


@router.get(
    "/{id_ride}",
    response_model=RideDetailResponse,
    summary="Ride details",
    responses={
        401: {"description": "Missing, invalid, expired, or revoked access token"},
        404: {"description": "Ride not found, or not visible to the caller"},
        422: {"description": "Invalid id_ride"},
    },
)
def get_ride(
    id_ride: Annotated[int, Path(gt=0, le=2**64 - 1, description="The ride's id_ride; send large IDs as strings.")],
    current_user_id: int = Depends(get_current_user_id),
    service: RideDetailService = Depends(get_ride_detail_service),
):
    """Full details of one ride (Authorization: Bearer <accessToken>), tailored to who is asking.

    - Everyone logged in can see `open` and `full` rides; other rides are visible only to their driver and to
      riders who booked them (anyone else gets 404).
    - `role` says how the caller relates to the ride: `driver`, `rider` or `viewer`.
    - `my_booking` is the caller's active booking (else their latest); `null` if they never booked.
    - For the driver only: `requests` (pending requests, accepted seats) and `bookings` (the active passengers and
      requests, with each rider's name and photo). Riders never see each other.
    """
    try:
        return service.get(id_ride, current_user_id)
    except RideNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="ride not found") from None
