import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator

VehicleType = Literal["car", "hatchback", "sedan", "suv", "bike"]

MIN_SEATS, MAX_SEATS = 1, 8  # matches chk_vehicle_seat_capacity

# Indian registration numbers, compared without spaces/hyphens:
#   standard  MH12AB1234, DL3CAB1234, KA051234  (state, district [+letter], 0–3 series letters, 4 digits)
#   BH series 22BH1234AA
_STANDARD_REG = re.compile(r"^[A-Z]{2}[0-9]{1,2}[A-Z]{0,4}[0-9]{4}$")
_BH_REG = re.compile(r"^[0-9]{2}BH[0-9]{4}[A-Z]{1,2}$")


def normalize_registration(value: str) -> str:
    return re.sub(r"[\s-]", "", value).upper()


def _required_text(value: str, field: str) -> str:
    value = " ".join(value.split())  # trim and collapse inner whitespace
    if not value:
        raise ValueError(f"{field} must not be blank")
    return value


class AddVehicleRequest(BaseModel):
    photo_url: str = Field(max_length=500, examples=["http://localhost:8000/media/3f2c9a.jpg"])
    make: str = Field(max_length=50, examples=["Maruti Suzuki"])
    model: str = Field(max_length=50, examples=["Swift"])
    registration_number: str = Field(max_length=20, examples=["MH 12 AB 1234"])
    colour: str = Field(max_length=30, examples=["Pearl White"])
    seat_capacity: int = Field(ge=MIN_SEATS, le=MAX_SEATS, examples=[4])
    vehicle_type: VehicleType = "car"

    @field_validator("photo_url")
    @classmethod
    def http_url(cls, v: str) -> str:
        v = v.strip()
        if not re.match(r"^https?://\S+$", v):
            raise ValueError("photo_url must be an http(s) URL from /v1/media/upload")
        return v

    @field_validator("make", "model", "colour")
    @classmethod
    def not_blank(cls, v: str, info) -> str:
        return _required_text(v, info.field_name)

    @field_validator("registration_number")
    @classmethod
    def valid_registration(cls, v: str) -> str:
        v = normalize_registration(v)
        if not (_STANDARD_REG.match(v) or _BH_REG.match(v)):
            raise ValueError("registration_number must be a valid Indian registration, e.g. MH12AB1234 or 22BH1234AA")
        return v


class VehicleResponse(BaseModel):
    id: str  # string: snowflake IDs exceed JS safe-integer range
    photo_url: str | None
    make: str
    model: str
    registration_number: str
    colour: str
    seat_capacity: int
    vehicle_type: VehicleType
    is_default: bool
    status: str
