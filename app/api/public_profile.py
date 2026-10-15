from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.schemas.public_profile import PublicProfileResponse
from app.services.public_profile_service import PublicProfileNotFound, PublicProfileService

router = APIRouter(prefix="/v1/users", tags=["users"])


@router.get(
    "/{id_user}/profile",
    response_model=PublicProfileResponse,
    summary="Another user's public profile",
    responses={
        401: {"description": "Missing, invalid, expired, or revoked access token"},
        404: {"description": "No such user, or you don't share a ride with them"},
    },
)
def public_profile(
    id_user: Annotated[int, Path(gt=0, le=2**64 - 1, description="The user's id; send large IDs as strings.")],
    current_user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Profile of a driver or rider you're dealing with (Authorization: Bearer <accessToken>).

    Visible for: yourself, anyone currently offering a bookable (open/full) ride, and anyone you share a
    ride with (they booked your ride, or you booked theirs). Everyone else gets 404.
    Never returns phone number, email or exact date of birth (only `age`).
    """
    try:
        return PublicProfileService(db).get(current_user_id, id_user)
    except PublicProfileNotFound:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="user not found") from None
