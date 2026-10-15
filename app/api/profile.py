from fastapi import APIRouter, Response, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.profile_repo import ProfileRepository, UserNotFoundError
from app.schemas.profile import SaveProfileRequest, ProfileResponse
from app.services.profile_service import ProfileService

router = APIRouter(prefix="/v1/auth", tags=["auth"])


def get_profile_service(db: Session = Depends(get_db)) -> ProfileService:
    return ProfileService(ProfileRepository(db))


@router.post("/profile", response_model=ProfileResponse, status_code=status.HTTP_201_CREATED)
def save_profile(
    req: SaveProfileRequest, response: Response, service: ProfileService = Depends(get_profile_service)
):
    """Create the profile, or fully replace it if one exists (201 on create, 200 on update)."""
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
