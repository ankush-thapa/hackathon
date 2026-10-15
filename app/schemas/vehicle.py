<<<<<<< Updated upstream
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
=======
import enum
import re
from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field, model_validator

_REGISTRATION_RE = re.compile(r"^[A-Z0-9-]{1,20}$")


class VehicleType(str, enum.Enum):
    hatchback = "hatchback"
    sedan = "sedan"
    suv = "suv"
    bike = "bike"


class VehicleStatus(str, enum.Enum):
    """Settable statuses. `deleted` is only reachable through DELETE."""

    active = "active"
    inactive = "inactive"


def _normalize_registration(v: str) -> str:
    v = "".join(v.split()).upper()  # same rule as Vehicle._normalize_registration_number
    if not _REGISTRATION_RE.fullmatch(v):
        raise ValueError("must be 1-20 letters, digits or '-'")
    return v


def _strip_required(v: str) -> str:
    v = v.strip()
    if not v:
        raise ValueError("must not be blank")
    return v


# Shared field types: trimmed non-blank text, and registration numbers without spaces, uppercased.
Make = Annotated[str, Field(max_length=50, examples=["Toyota"]), AfterValidator(_strip_required)]
Model = Annotated[str, Field(max_length=50, examples=["Corolla"]), AfterValidator(_strip_required)]
Color = Annotated[str, Field(max_length=30, examples=["White"]), AfterValidator(_strip_required)]
Registration = Annotated[str, Field(max_length=30, examples=["KA 01 AB 1234"]), AfterValidator(_normalize_registration)]
Seats = Annotated[int, Field(ge=1, le=8, examples=[4])]


class VehicleCreate(BaseModel):
    make: Make
    model: Model
    color: Color
    registrationNumber: Registration
    seatCapacity: Seats
    vehicleType: VehicleType
    isDefault: bool = False  # the user's first vehicle becomes default regardless


class VehicleUpdate(BaseModel):
    """Send only the fields to change."""

    make: Make | None = None
    model: Model | None = None
    color: Color | None = None
    registrationNumber: Registration | None = None
    seatCapacity: Seats | None = None
    vehicleType: VehicleType | None = None
    isDefault: bool | None = None
    status: VehicleStatus | None = None

    @model_validator(mode="after")
    def _non_empty_and_no_nulls(self) -> "VehicleUpdate":
        if not self.model_fields_set:
            raise ValueError("provide at least one field to update")
        nulls = sorted(f for f in self.model_fields_set if getattr(self, f) is None)
        if nulls:
            raise ValueError(f"cannot be null: {', '.join(nulls)}")
        return self


class VehicleResponse(BaseModel):
    vehicleId: str  # string: snowflake IDs exceed JS safe-integer range
    make: str
    model: str
    color: str
    registrationNumber: str
    seatCapacity: int
    vehicleType: VehicleType
    isDefault: bool
    status: VehicleStatus
    createdAt: datetime  # UTC
    updatedAt: datetime  # UTC
>>>>>>> Stashed changes
