from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator

_EMAIL_RE = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
_PHONE_RE = r"^\+[1-9]\d{7,14}$"  # E.164


class RegisterRequest(BaseModel):
    email: str = Field(max_length=254, pattern=_EMAIL_RE, examples=["jane@example.com"])
    phone: str = Field(pattern=_PHONE_RE, examples=["+971501234567"])
    password: str = Field(min_length=8, max_length=50)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if not (any(c.isalpha() for c in v) and any(c.isdigit() for c in v)):
            raise ValueError("password must contain at least one letter and one digit")
        return v


class RegisterResponse(BaseModel):
    userId: str
    email: str
    phone: str


class LoginRequest(BaseModel):
    """Exactly one of email or phone, plus the password."""

    email: str | None = Field(default=None, max_length=254, pattern=_EMAIL_RE, examples=["jane@example.com"])
    phone: str | None = Field(default=None, pattern=_PHONE_RE, examples=["+971501234567"])
    password: str = Field(min_length=1, max_length=50)

    @field_validator("email", "phone", mode="before")
    @classmethod
    def normalize(cls, v: object, info) -> object:
        # Before the pattern check, so pasted values with stray spaces still match.
        if not isinstance(v, str):
            return v
        v = v.strip()
        return v.lower() if info.field_name == "email" else v

    @model_validator(mode="after")
    def exactly_one_identifier(self) -> "LoginRequest":
        if (self.email is None) == (self.phone is None):
            raise ValueError("provide exactly one of email or phone")
        return self


class LoginResponse(BaseModel):
    accessToken: str
    tokenType: str = "Bearer"
    expiresIn: int  # seconds until accessToken expires
    refreshToken: str  # single use; send to /v1/auth/refresh for a new pair
    sessionExpiresAt: datetime  # UTC; after this, log in again
    userId: str
    sessionId: str


class MeResponse(BaseModel):
    userId: str


class RefreshRequest(BaseModel):
    refreshToken: str = Field(min_length=1, max_length=200)


class SessionInfo(BaseModel):
    sessionId: str
    current: bool  # the session that made this request
    userAgent: str | None
    ipAddress: str | None
    createdAt: datetime  # UTC
    expiresAt: datetime  # UTC
