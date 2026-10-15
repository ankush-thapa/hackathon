from pydantic import BaseModel, Field, field_validator

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
