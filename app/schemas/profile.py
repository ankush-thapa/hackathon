from datetime import date

from pydantic import BaseModel, Field, field_validator

from app.models.user_profile import Gender


class SaveProfileRequest(BaseModel):
    # TODO: drop userId and take it from the access token once login exists.
    userId: int = Field(gt=0, examples=[236357292134498304])
    fullName: str = Field(min_length=1, max_length=100, examples=["Jane Doe"])
    photoUrl: str | None = Field(default=None, max_length=500)
    about: str | None = Field(default=None, max_length=500)
    dateOfBirth: date | None = Field(default=None, examples=["1995-04-12"])
    gender: Gender | None = None

    @field_validator("fullName")
    @classmethod
    def strip_full_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("fullName must not be blank")
        return v

    @field_validator("dateOfBirth")
    @classmethod
    def not_in_future(cls, v: date | None) -> date | None:
        if v is not None and v >= date.today():
            raise ValueError("dateOfBirth must be in the past")
        return v


class ProfileResponse(BaseModel):
    userId: str  # string: snowflake IDs exceed JS safe-integer range
    fullName: str
    photoUrl: str | None
    about: str | None
    dateOfBirth: date | None
    gender: Gender | None


class MyProfileResponse(ProfileResponse):
    age: int | None  # whole years, computed from dateOfBirth
    email: str | None
    phoneNumber: str | None
