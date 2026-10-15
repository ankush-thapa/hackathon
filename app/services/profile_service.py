from app.repositories.profile_repo import ProfileRepository
from app.schemas.profile import SaveProfileRequest


class ProfileService:
    def __init__(self, profiles: ProfileRepository):
        self._profiles = profiles

    def upsert(self, req: SaveProfileRequest) -> bool:
        # Raises UserNotFoundError. Returns True if the profile was newly created.
        return self._profiles.upsert(
            {
                "id_user": req.userId,
                "full_name": req.fullName,
                "photo_url": req.photoUrl,
                "about": req.about,
                "date_of_birth": req.dateOfBirth,
                "gender": req.gender.value if req.gender else None,
            }
        )
