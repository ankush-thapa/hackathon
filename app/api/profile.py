from fastapi import APIRouter, Response, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.db.session import get_db
from app.repositories.profile_repo import ProfileRepository, UserNotFoundError
from app.schemas.profile import MyProfileResponse, ProfileResponse, SaveProfileRequest
from app.services.profile_service import ProfileNotFoundError, ProfileService

router = APIRouter(prefix="/v1/auth", tags=["auth"])


def get_profile_service(db: Session = Depends(get_db)) -> ProfileService:
    return ProfileService(ProfileRepository(db))


@router.get(
    "/profile",
    response_model=MyProfileResponse,
    summary="Get my profile",
    responses={
        401: {"description": "Missing, invalid, expired, or revoked access token"},
        404: {"description": "No profile saved yet: create one with POST /v1/auth/profile"},
    },
)
def get_profile(
    current_user_id: int = Depends(get_current_user_id),
    service: ProfileService = Depends(get_profile_service),
):
    """The logged-in user's profile (Authorization: Bearer <accessToken>), with `age` and contact details."""
    try:
        return service.get(current_user_id)
    except ProfileNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="profile not found") from None


@router.post("/profile", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
def save_profile(
    req: SaveProfileRequest, response: Response,
    current_user_id: int = Depends(get_current_user_id),
    service: ProfileService = Depends(get_profile_service)
):
    """Create the profile, or fully replace it if one exists (201 on create, 200 on update)."""
    if req.userId is not None and req.userId != current_user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="cannot update another user profile")
    req = req.model_copy(update={"userId": current_user_id})
    try:
        created = service.upsert(req)
    except UserNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="user not found")
    response.status_code = status.HTTP_201_CREATED if created else status.HTTP_200_OK
    return ProfileResponse(
        userId=str(req.userId),
        fullName=req.fullName,
        photoUrl=req.photoUrl,
        about=req.about,
        dateOfBirth=req.dateOfBirth,
        gender=req.gender,
    )
