from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_session
from app.db.session import get_db
from app.repositories.station_repo import StationRepository
from app.schemas.station import StationListResponse

router = APIRouter(prefix="/v1/stations", tags=["stations"])


@router.get(
    "", response_model=StationListResponse, summary="List stations",
    responses={401: {"description": "Missing, invalid, expired, or revoked access token"}},
)
@require_session
def list_stations(
    search: str | None = Query(default=None, max_length=100, description="Case-insensitive station-name substring."),
    include_inactive: bool = Query(default=False, description="Include inactive stations as well as active ones."),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    """List pickup/drop-off stations using Authorization: Bearer <accessToken>.

    Active stations are returned by default, ordered by station_name then id_station.
    total counts all matching stations before pagination. No matches returns an empty list.
    """
    return StationRepository(db).list(
        search=search, include_inactive=include_inactive, limit=limit, offset=offset,
    )
