import enum
import re
from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator, model_validator


class VehicleType(str, enum.Enum):
    car = "car"
    hatchback = "hatchback"
    sedan = "sedan"
    suv = "suv"
    bike = "bike"


class VehicleStatus(str, enum.Enum):
    """Settable statuses. Deleted vehicles are hidden by the API."""
    active = "active"
    inactive = "inactive"


_STANDARD_REG = re.compile(r"^[A-Z]{2}[0-9]{1,2}[A-Z]{0,4}[0-9]{4}$")
_BH_REG = re.compile(r"^[0-9]{2}BH[0-9]{4}[A-Z]{1,2}$")
_REGISTRATION_RE = re.compile(r"^[A-Z0-9]{1,20}$")


def normalize_registration(value: str) -> str:
    # Both request formats must store the same canonical registration.
    return re.sub(r"[\s-]", "", value).upper()


def _normalize_registration(value: str) -> str:
    value = normalize_registration(value)
    if not _REGISTRATION_RE.fullmatch(value):
        raise ValueError("must be 1-20 letters or digits, with optional spaces/hyphens")
    return value


def _strip_required(value: str) -> str:
    value = " ".join(value.split())
    if not value:
        raise ValueError("must not be blank")
    return value


def _http_url(value: str) -> str:
    value = value.strip()
    if not re.match(r"^https?://\S+$", value):
        raise ValueError("must be an http(s) URL from /v1/media/upload")
    return value


Make = Annotated[str, Field(max_length=50, examples=["Toyota"]), AfterValidator(_strip_required)]
Model = Annotated[str, Field(max_length=50, examples=["Corolla"]), AfterValidator(_strip_required)]
Color = Annotated[str, Field(max_length=30, examples=["White"]), AfterValidator(_strip_required)]
Registration = Annotated[str, Field(max_length=30, examples=["KA 01 AB 1234"]), AfterValidator(_normalize_registration)]
Seats = Annotated[int, Field(ge=1, le=8, examples=[4])]
PhotoUrl = Annotated[str, Field(max_length=500), AfterValidator(_http_url)]


class AddVehicleRequest(BaseModel):
    """Photo-based snake_case contract used by the current frontend."""
    model_config = ConfigDict(extra="forbid")
    photo_url: PhotoUrl
    make: Make
    model: Model
    registration_number: str = Field(max_length=20, examples=["MH 12 AB 1234"])
    colour: Color
    seat_capacity: Seats
    vehicle_type: VehicleType = VehicleType.car

    @field_validator("registration_number")
    @classmethod
    def valid_registration(cls, value: str) -> str:
        value = normalize_registration(value)
        if not (_STANDARD_REG.fullmatch(value) or _BH_REG.fullmatch(value)):
            raise ValueError("registration_number must be a valid Indian registration, e.g. MH12AB1234 or 22BH1234AA")
        return value


class AddVehicleResponse(BaseModel):
    id: str
    photo_url: str | None
    make: str
    model: str
    registration_number: str
    colour: str
    seat_capacity: int
    vehicle_type: VehicleType
    is_default: bool
    status: VehicleStatus


class VehicleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    make: Make
    model: Model
    color: Color
    registrationNumber: Registration
    seatCapacity: Seats
    vehicleType: VehicleType
    isDefault: bool = False
    photoUrl: PhotoUrl | None = None


class VehicleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    make: Make | None = None
    model: Model | None = None
    color: Color | None = None
    registrationNumber: Registration | None = None
    seatCapacity: Seats | None = None
    vehicleType: VehicleType | None = None
    isDefault: bool | None = None
    status: VehicleStatus | None = None
    photoUrl: PhotoUrl | None = None

    @model_validator(mode="after")
    def _non_empty_and_no_nulls(self) -> "VehicleUpdate":
        if not self.model_fields_set:
            raise ValueError("provide at least one field to update")
        nulls = sorted(field for field in self.model_fields_set if field != "photoUrl" and getattr(self, field) is None)
        if nulls:
            raise ValueError(f"cannot be null: {', '.join(nulls)}")
        return self


class VehicleResponse(BaseModel):
    vehicleId: str
    make: str
    model: str
    color: str
    registrationNumber: str
    seatCapacity: int
    vehicleType: VehicleType
    isDefault: bool
    status: VehicleStatus
    createdAt: datetime
    updatedAt: datetime
    photoUrl: str | None = None
