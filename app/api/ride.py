from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_session
from app.db.session import get_db
from app.repositories.ride_repo import RideRepository
from app.schemas.ride import RideListResponse
from app.services.ride_service import InvalidCursorError, RideService, StationNotFoundError

router = APIRouter(prefix="/v1/rides", tags=["rides"])


def get_ride_service(db: Session = Depends(get_db)) -> RideService:
    return RideService(RideRepository(db))


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
