from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import require_session
from app.db.session import get_db
from app.repositories.notification_repo import NotificationRepository
from app.schemas.notification import (
    MarkAllReadResponse, NotificationItem, NotificationListResponse, SendNotificationRequest,
)
from app.services.notification_service import (
    BookingNotOnRideError,
    NotificationNotFoundError,
    NotificationService,
    NotRideParticipantError,
    RideNotFoundError,
)

router = APIRouter(prefix="/v1/notifications", tags=["notifications"])

_UNAUTHORIZED = {401: {"description": "Missing, invalid, expired, or revoked session"}}


def get_notification_service(db: Session = Depends(get_db)) -> NotificationService:
    return NotificationService(NotificationRepository(db))


@router.get("", response_model=NotificationListResponse, responses=_UNAUTHORIZED)
@require_session
def list_notifications(
    response: Response,
    current_user_id: int,
    limit: Annotated[int, Query(ge=1, le=50, description="Max notifications to return.")] = 20,
    service: NotificationService = Depends(get_notification_service),
):
    """Unread notifications for the caller, newest first. Meant to be polled by the UI.

    Read notifications are never returned: once the user opens one, call
    POST /v1/notifications/{idNotification}/read and it drops out of this list.
    """
    response.headers["Cache-Control"] = "no-store"
    return service.unread(current_user_id, limit)


@router.post(
    "", response_model=NotificationItem, status_code=status.HTTP_201_CREATED,
    responses={
        **_UNAUTHORIZED,
        403: {"description": "Caller is not the ride's driver or a rider who booked it"},
        404: {"description": "Ride missing, or booking not on that ride"},
        422: {"description": "Recipient not part of the ride, or invalid fields"},
    },
)
@require_session
def send_notification(
    req: SendNotificationRequest,
    current_user_id: int,
    service: NotificationService = Depends(get_notification_service),
):
    """Send a notification to another user on the same ride (driver or a rider who booked it).

    It shows up in the recipient's GET /v1/notifications until they mark it read.
    """
    try:
        return service.send(current_user_id, req)
    except RideNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="ride not found") from None
    except BookingNotOnRideError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="booking not found on this ride") from None
    except NotRideParticipantError as e:
        if e.who == "sender":
            raise HTTPException(status.HTTP_403_FORBIDDEN, detail="you are not part of this ride") from None
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="idUser is not part of this ride") from None


@router.post(
    "/read-all", response_model=MarkAllReadResponse,
    responses=_UNAUTHORIZED,
)
@require_session
def mark_all_read(current_user_id: int, service: NotificationService = Depends(get_notification_service)):
    """Mark every unread notification of the caller as read."""
    return MarkAllReadResponse(marked=service.mark_all_read(current_user_id))


@router.post(
    "/{idNotification}/read", status_code=status.HTTP_204_NO_CONTENT,
    responses={**_UNAUTHORIZED, 404: {"description": "No such notification for the caller"}},
)
@require_session
def mark_read(
    idNotification: Annotated[int, Path(gt=0, le=2**64 - 1)],
    current_user_id: int,
    service: NotificationService = Depends(get_notification_service),
):
    """Mark one notification as read (idempotent). Send the id as returned, i.e. the string."""
    try:
        service.mark_read(current_user_id, idNotification)
    except NotificationNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="notification not found") from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)
