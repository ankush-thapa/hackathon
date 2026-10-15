from datetime import date, datetime, timezone

from app.repositories.profile_repo import ProfileRepository
from app.schemas.profile import MyProfileResponse, SaveProfileRequest


class ProfileNotFoundError(Exception):
    pass


def age_on(date_of_birth: date | None, today: date) -> int | None:
    """Whole years completed on `today`."""
    if date_of_birth is None:
        return None
    return today.year - date_of_birth.year - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))


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

    def get(self, id_user: int) -> MyProfileResponse:
        """The user's own profile. Raises ProfileNotFoundError if none has been saved yet."""
        row = self._profiles.get(id_user)
        if row is None:
            raise ProfileNotFoundError
        dob = row["date_of_birth"]
        return MyProfileResponse(
            userId=str(row["id_user"]),
            fullName=row["full_name"],
            photoUrl=row["photo_url"],
            about=row["about"],
            dateOfBirth=dob,
            age=age_on(dob, datetime.now(timezone.utc).date()),
            gender=row["gender"],
            email=row["email"],
            phoneNumber=row["phone_number"],
        )
