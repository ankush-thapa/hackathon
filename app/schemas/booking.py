from datetime import datetime, timezone
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.ride_booking import BookingStatus


class BookRideRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id_ride: int = Field(gt=0, le=2**64 - 1, description="The ride to book; send large IDs as strings.")
    seats: int = Field(ge=1, le=8, strict=True, description="Number of seats to request.")
    rider_note: str | None = Field(default=None, max_length=255)

    @field_validator("id_ride", mode="before")
    @classmethod
    def reject_boolean_id(cls, value):
        if isinstance(value, bool):
            raise ValueError("id_ride must be a positive integer")
        return value

    @field_validator("rider_note")
    @classmethod
    def normalize_note(cls, value):
        return (value.strip() or None) if value is not None else None


class CancelBookingRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str | None = Field(default=None, max_length=255)

    @field_validator("reason")
    @classmethod
    def normalize_reason(cls, value):
        return (value.strip() or None) if value is not None else None


class RejectBookingRequest(CancelBookingRequest):
    """Same shape as a cancel: an optional reason shown to the rider."""


class BookingResponse(BaseModel):
    id_booking: str
    id_ride: str
    id_rider: str
    id_driver: str
    seats_booked: int
    price_per_seat: Decimal
    total_amount: Decimal
    rider_note: str | None
    status: BookingStatus
    reject_reason: str | None = None
    cancel_reason: str | None = None
    responded_at: datetime | None = None  # when the driver approved
    cancelled_at: datetime | None = None
    version: int
    created_at: datetime
    updated_at: datetime

    @field_validator("id_booking", "id_ride", "id_rider", "id_driver", mode="before")
    @classmethod
    def serialize_large_ids(cls, value):
        return str(value)

    @field_validator("created_at", "updated_at", "responded_at", "cancelled_at")
    @classmethod
    def utc_datetime(cls, value):
        if value is None:
            return None
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)
