from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Header, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.repositories.booking_repo import (
    BookingNotCancellableError,
    BookingNotFoundError,
    BookingNotPendingError,
    BookingRepository,
    DuplicateBookingError,
    NotEnoughSeatsError,
    NotRideDriverError,
    OwnRideError,
    RideAlreadyStartedError,
    RideNotBookableError,
    RideNotFoundError,
)
from app.repositories.notification_repo import NotificationRepository
from app.schemas.booking import BookingResponse, BookRideRequest, CancelBookingRequest, RejectBookingRequest
from app.services.booking_service import BookingService
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/v1/ride/booking", tags=["bookings"])


def get_booking_service(db: Session = Depends(get_db)) -> BookingService:
    return BookingService(BookingRepository(db), NotificationService(NotificationRepository(db)))


@router.post(
    "",
    response_model=BookingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Book a ride",
    responses={
        401: {"description": "Missing, invalid, expired, or revoked access token"},
        403: {"description": "The ride is the caller's own"},
        404: {"description": "Ride not found"},
        409: {"description": "Ride not open or already departed, not enough seats, or already booked by this rider"},
        422: {"description": "Invalid id_ride or seats"},
    },
)
def book_ride(
    request: BookRideRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key", min_length=8, max_length=128),
    current_user_id: int = Depends(get_current_user_id),
    service: BookingService = Depends(get_booking_service),
):
    """Request `seats` seats on a ride using Authorization: Bearer <accessToken>.

    The booking starts as `requested`; the driver then accepts or rejects it. The price per seat is
    copied from the ride at booking time and total_amount = price_per_seat * seats.
    Optional Idempotency-Key (8-128 chars) makes identical retries return the same booking
    in its current state; using the same key with another payload returns 409.
    """
    try:
        booking = service.book(current_user_id, request, idempotency_key)
    except RideNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="ride not found") from None
    except OwnRideError:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="you cannot book your own ride") from None
    except RideNotBookableError:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="ride is not open for booking") from None
    except NotEnoughSeatsError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=f"not enough seats: {e.available} available") from None
    except DuplicateBookingError:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="you already have an active booking on this ride") from None
    return BookingResponse.model_validate(booking)


BookingId = Annotated[int, Path(gt=0, le=2**64 - 1, description="The booking's id_booking; send large IDs as strings.")]
_CHANGE_RESPONSES = {
    401: {"description": "Missing, invalid, expired, or revoked access token"},
    404: {"description": "Booking not found, or the caller is not its rider or the ride's driver"},
    422: {"description": "Invalid id_booking or body"},
}


@router.post(
    "/{id_booking}/approve",
    response_model=BookingResponse,
    summary="Approve a ride request (driver)",
    responses={
        **_CHANGE_RESPONSES,
        403: {"description": "The caller is the rider, not the ride's driver"},
        409: {"description": "Booking is not pending, ride not open or already departed, or not enough seats left"},
    },
)
def approve_booking(
    id_booking: BookingId,
    current_user_id: int = Depends(get_current_user_id),
    service: BookingService = Depends(get_booking_service),
):
    """The ride's driver accepts a `requested` booking using Authorization: Bearer <accessToken>.

    The booking becomes `accepted` and its seats are taken from the ride's `available_seats`; the ride
    becomes `full` when none are left.
    """
    try:
        booking = service.approve(current_user_id, id_booking)
    except BookingNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="booking not found") from None
    except NotRideDriverError:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="only the ride's driver can approve a request") from None
    except BookingNotPendingError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=f"booking is not awaiting approval (status: {e.status})") from None
    except RideNotBookableError:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="ride is not open or has already departed") from None
    except NotEnoughSeatsError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=f"not enough seats: {e.available} available") from None
    return BookingResponse.model_validate(booking)


@router.post(
    "/{id_booking}/reject",
    response_model=BookingResponse,
    summary="Reject a ride request (driver)",
    responses={
        **_CHANGE_RESPONSES,
        403: {"description": "The caller is the rider, not the ride's driver"},
        409: {"description": "Booking is not pending, or the ride has started, finished or been cancelled"},
    },
)
def reject_booking(
    id_booking: BookingId,
    request: RejectBookingRequest | None = None,
    current_user_id: int = Depends(get_current_user_id),
    service: BookingService = Depends(get_booking_service),
):
    """The ride's driver declines a `requested` booking using Authorization: Bearer <accessToken>.

    The booking becomes `rejected` (with the optional `reason`) and the rider is notified. A request never held
    seats, so the ride's `available_seats` is unchanged.
    """
    try:
        booking = service.reject(current_user_id, id_booking, request.reason if request else None)
    except BookingNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="booking not found") from None
    except NotRideDriverError:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="only the ride's driver can reject a request") from None
    except BookingNotPendingError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=f"booking is not awaiting a decision (status: {e.status})") from None
    except RideAlreadyStartedError:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="ride has already started or finished") from None
    return BookingResponse.model_validate(booking)


@router.post(
    "/{id_booking}/cancel",
    response_model=BookingResponse,
    summary="Cancel a ride request or booking",
    responses={
        **_CHANGE_RESPONSES,
        409: {"description": "Booking already finished or cancelled, or the ride has started"},
    },
)
def cancel_booking(
    id_booking: BookingId,
    request: CancelBookingRequest | None = None,
    current_user_id: int = Depends(get_current_user_id),
    service: BookingService = Depends(get_booking_service),
):
    """Cancel a `requested` or `accepted` booking using Authorization: Bearer <accessToken>.

    The rider cancels their own request (`cancelled_by_rider`) and the ride's driver can cancel a passenger
    (`cancelled_by_driver`). An accepted booking gives its seats back to the ride, which reopens if it was full.
    """
    try:
        booking = service.cancel(current_user_id, id_booking, request.reason if request else None)
    except BookingNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="booking not found") from None
    except BookingNotCancellableError as e:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=f"booking cannot be cancelled (status: {e.status})") from None
    except RideAlreadyStartedError:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="ride has already started or finished") from None
    return BookingResponse.model_validate(booking)
