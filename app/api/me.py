from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.core.pagination import InvalidCursorError
from app.db.session import get_db
from app.repositories.my_ride_repo import MyRideRepository
from app.schemas.my_ride import MyBookingsResponse, MyRidesResponse, MyRideScope
from app.services.my_ride_service import MyRideService

router = APIRouter(prefix="/v1/me", tags=["me"])

_AUTH_RESPONSES = {
    401: {"description": "Missing, invalid, expired, or revoked access token"},
    422: {"description": "Invalid `when`, `page_size`, or `cursor`"},
}
Scope = Annotated[MyRideScope, Query(description="`upcoming` (default, soonest first), `past` or `all` (most recent first).")]
PageSize = Annotated[int, Query(ge=1, le=50, description="Items per page.")]
Cursor = Annotated[str | None, Query(description="`next_page` or `prev_page` from a previous response.")]


def get_my_ride_service(db: Session = Depends(get_db)) -> MyRideService:
    return MyRideService(MyRideRepository(db))


@router.get("/rides", response_model=MyRidesResponse, summary="Rides I offered (driver)", responses=_AUTH_RESPONSES)
def list_my_rides(
    when: Scope = MyRideScope.upcoming,
    page_size: PageSize = 20,
    cursor: Cursor = None,
    current_user_id: int = Depends(get_current_user_id),
    service: MyRideService = Depends(get_my_ride_service),
):
    """Rides the logged-in driver offered, each with `requests` (pending requests and accepted seats)."""
    try:
        return service.list_offered(id_user=current_user_id, scope=when, page_size=page_size, cursor=cursor)
    except InvalidCursorError:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid cursor") from None


@router.get("/bookings", response_model=MyBookingsResponse, summary="Bookings I made (rider)", responses=_AUTH_RESPONSES)
def list_my_bookings(
    when: Scope = MyRideScope.upcoming,
    page_size: PageSize = 20,
    cursor: Cursor = None,
    current_user_id: int = Depends(get_current_user_id),
    service: MyRideService = Depends(get_my_ride_service),
):
    """The logged-in rider's bookings, one row per booking, each with the booked `ride` nested inside.

    `upcoming` is bookings still `requested` or `accepted` on rides that haven't left; everything else is `past`.
    """
    try:
        return service.list_booked(id_user=current_user_id, scope=when, page_size=page_size, cursor=cursor)
    except InvalidCursorError:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, detail="invalid cursor") from None
