from datetime import datetime, timezone

from pydantic import BaseModel, field_validator


class PublicVehicle(BaseModel):
    make: str
    model: str
    color: str
    vehicleType: str


class PublicProfileResponse(BaseModel):
    """What one user may see about another. Never includes phone, email or exact date of birth."""

    userId: str  # string: snowflake IDs exceed JS safe-integer range
    fullName: str | None  # null if they haven't saved a profile yet
    photoUrl: str | None
    about: str | None
    gender: str | None
    age: int | None  # whole years, from date of birth
    memberSince: datetime  # UTC, when the account was created
    ridesDriven: int  # completed rides as driver
    ridesTaken: int  # completed rides as rider
    vehicle: PublicVehicle | None  # their default active vehicle, if any

    @field_validator("memberSince")
    @classmethod
    def utc_datetime(cls, value):
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
