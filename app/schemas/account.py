from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.schemas.auth import RegisterRequest, LoginRequest


class PasswordConfirmation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    current_password: str = Field(min_length=1, max_length=50)


class ChangePasswordRequest(PasswordConfirmation):
    new_password: str = Field(min_length=8, max_length=50, description="At least one letter and digit.")

    @field_validator("new_password")
    @classmethod
    def strong_password(cls, value):
        return RegisterRequest.password_strength(value)


class ContactUpdateRequest(PasswordConfirmation):
    email: str | None = Field(default=None, max_length=254)
    phone: str | None = None

    @model_validator(mode="after")
    def contacts(self):
        fields = self.model_fields_set & {"email", "phone"}
        if not fields:
            raise ValueError("provide email and/or phone")
        for name in fields:
            value = getattr(self, name)
            if value is None:
                raise ValueError(f"{name} cannot be null")
            checked = LoginRequest(**{name: value, "password": "x"})
            setattr(self, name, getattr(checked, name))
        return self


class AccountResponse(BaseModel):
    userId: str
    email: str | None
    phone: str | None
    status: str
