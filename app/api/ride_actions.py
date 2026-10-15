from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query
from pydantic import ValidationError
from fastapi.exceptions import RequestValidationError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.models.ride_booking import BookingStatus
from app.schemas.booking import BookingResponse, CancelBookingRequest
from app.schemas.ride import OfferRideResponse
from app.schemas.ride_actions import RideUpdateRequest, RideBookingListResponse, RiderBookingItem, ExpireRequestsResponse
from app.services.ride_actions import RideActions

router = APIRouter(tags=["ride lifecycle"], responses={401: {"description": "Missing/invalid session"}, 403: {"description": "Forbidden"}, 404: {"description": "Resource not found"}, 409: {"description": "State conflict"}})
Id = Annotated[int, Path(gt=0, le=2**64-1)]


def actions(db: Session = Depends(get_db)):
    return RideActions(db)


def ride_response(ride):
    return OfferRideResponse.model_validate({key: getattr(ride,key) for key in OfferRideResponse.model_fields})


def booking_response(booking):
    return BookingResponse.model_validate({key: getattr(booking,key) for key in BookingResponse.model_fields})


@router.get("/v1/rides/{id_ride}/bookings", response_model=RideBookingListResponse)
def list_ride_bookings(id_ride: Id, status: BookingStatus | None = None,
                       cursor: int | None = Query(default=None, gt=0, le=2**64-1),
                       limit: int = Query(default=20, ge=1, le=50),
                       user: int = Depends(get_current_user_id), service: RideActions = Depends(actions)):
    """Driver-only authoritative requests/passenger list. Pass next_cursor as cursor."""
    rows, cursor = service.list_bookings(id_ride, user, status, cursor, limit)
    return RideBookingListResponse(items=[RiderBookingItem(**booking_response(b).model_dump(),
        rider_name=name, rider_photo_url=photo) for b,name,photo in rows], next_cursor=cursor)


@router.patch("/v1/rides/{id_ride}", response_model=OfferRideResponse)
def update_ride(id_ride: Id, request: RideUpdateRequest,
                user: int = Depends(get_current_user_id), service: RideActions = Depends(actions)):
    """Partial update using offer payload field names; omitted fields are retained.

    Vehicle/route/departure/price cannot change while active bookings exist.
    total_seats cannot fall below the seats held by pending requests and accepted bookings. notes and estimated_arrival_time may be cleared with null.
    """
    try:
        return ride_response(service.update(id_ride, user, request))
    except ValidationError as exc:
        raise RequestValidationError(exc.errors()) from None


@router.post("/v1/rides/{id_ride}/cancel", response_model=OfferRideResponse)
def cancel_ride(id_ride: Id, request: CancelBookingRequest | None = None,
                user: int = Depends(get_current_user_id), service: RideActions = Depends(actions)):
    """Cancel the entire ride and all active bookings; optional body: {"reason": "..."}."""
    return ride_response(service.transition(id_ride, user, "cancel", request.reason if request else None))


@router.post("/v1/rides/{id_ride}/start", response_model=OfferRideResponse)
def start_ride(id_ride: Id, user: int = Depends(get_current_user_id), service: RideActions = Depends(actions)):
    """Driver starts the ride at/after departure. No request body; pending requests expire."""
    return ride_response(service.transition(id_ride, user, "start"))


@router.post("/v1/rides/{id_ride}/complete", response_model=OfferRideResponse)
def complete_ride(id_ride: Id, user: int = Depends(get_current_user_id), service: RideActions = Depends(actions)):
    """Driver completes a started ride and accepted bookings. No request body."""
    return ride_response(service.transition(id_ride, user, "complete"))


@router.post("/v1/rides/{id_ride}/expire-requests", response_model=ExpireRequestsResponse)
def expire_requests(id_ride: Id, user: int = Depends(get_current_user_id), service: RideActions = Depends(actions)):
    """Driver expires pending requests after departure; safe to repeat. No request body."""
    return ExpireRequestsResponse(expired=service.expire(id_ride, user))


@router.get("/v1/ride/booking/{id_booking}", response_model=BookingResponse)
def booking_detail(id_booking: Id, user: int = Depends(get_current_user_id), service: RideActions = Depends(actions)):
    return booking_response(service.booking(id_booking, user))
