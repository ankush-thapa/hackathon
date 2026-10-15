from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.repositories.ride_repo import (
    RideConflictError,
    RideRepository,
    StationNotFoundError,
    VehicleCapacityError,
    VehicleInactiveError,
    VehicleNotFoundError,
)
from app.schemas.ride import OfferRideRequest, OfferRideResponse
from app.services.ride_service import DepartureInPastError, RideService

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
