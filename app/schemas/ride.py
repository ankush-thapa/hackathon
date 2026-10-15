from datetime import datetime, timezone
from decimal import Decimal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.ride import RideStatus


class OfferRideRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id_vehicle: int = Field(gt=0, le=2**64 - 1, description="An active vehicle owned by the logged-in driver; send large IDs as strings.")
    id_source_station: int = Field(gt=0, le=2**32 - 1)
    id_destination_station: int = Field(gt=0, le=2**32 - 1)
    departure_time: AwareDatetime = Field(description="Future departure time with a timezone, e.g. 2030-01-01T09:00:00+05:30.")
    estimated_arrival_time: AwareDatetime | None = None
    total_seats: int = Field(ge=1, le=8, strict=True)
    price_per_seat: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=10, decimal_places=2)
    notes: str | None = Field(default=None, max_length=500)

    @field_validator("id_vehicle", "id_source_station", "id_destination_station", mode="before")
    @classmethod
    def reject_boolean_ids(cls, value):
        if isinstance(value, bool):
            raise ValueError("IDs must be positive integers")
        return value

    @field_validator("departure_time", "estimated_arrival_time")
    @classmethod
    def normalize_datetime(cls, value):
        if value is None:
            return None
        value = value.astimezone(timezone.utc)
        return value.replace(microsecond=(value.microsecond // 1000) * 1000)

    @field_validator("price_per_seat")
    @classmethod
    def normalize_price(cls, value):
        return value.quantize(Decimal("0.01"))

    @field_validator("notes")
    @classmethod
    def normalize_notes(cls, value):
        return (value.strip() or None) if value is not None else None

    @model_validator(mode="after")
    def validate_route_and_times(self):
        if self.id_source_station == self.id_destination_station:
            raise ValueError("source and destination stations must be different")
        if self.estimated_arrival_time is not None and self.estimated_arrival_time <= self.departure_time:
            raise ValueError("estimated_arrival_time must be after departure_time")
        return self


class OfferRideResponse(BaseModel):
    id_ride: str
    id_driver: str
    id_vehicle: str
    id_source_station: int
    id_destination_station: int
    departure_time: datetime
    estimated_arrival_time: datetime | None
    total_seats: int
    available_seats: int
    price_per_seat: Decimal
    notes: str | None
    status: RideStatus
    version: int
    created_at: datetime
    updated_at: datetime

    @field_validator("id_ride", "id_driver", "id_vehicle", mode="before")
    @classmethod
    def serialize_large_ids(cls, value):
        return str(value)

    @field_validator("departure_time", "estimated_arrival_time", "created_at", "updated_at")
    @classmethod
    def utc_datetime(cls, value):
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
