from datetime import datetime
from decimal import Decimal

from pydantic import AwareDatetime, BaseModel, Field, field_validator, model_validator

from app.models.ride_booking import BookingStatus
from app.schemas.booking import BookingResponse, CancelBookingRequest
from app.schemas.ride import OfferRideRequest


class RideUpdateRequest(OfferRideRequest):
    # Same names and validation as offer; omitted fields are retained.
    id_vehicle: int | None = Field(default=None, gt=0, le=2**64-1)
    id_source_station: int | None = Field(default=None, gt=0, le=2**32-1)
    id_destination_station: int | None = Field(default=None, gt=0, le=2**32-1)
    departure_time: AwareDatetime | None = None
    total_seats: int | None = Field(default=None, ge=1, le=8, strict=True)
    price_per_seat: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)

    @field_validator("price_per_seat")
    @classmethod
    def normalize_price(cls, value):
        return value.quantize(Decimal("0.01")) if value is not None else None

    @model_validator(mode="after")
    def validate_route_and_times(self):
        if not self.model_fields_set:
            raise ValueError("provide at least one field to update")
        for key in self.model_fields_set - {"notes", "estimated_arrival_time"}:
            if getattr(self, key) is None:
                raise ValueError(f"{key} cannot be null")
        if self.id_source_station is not None and self.id_source_station == self.id_destination_station:
            raise ValueError("source and destination must differ")
        if self.departure_time and self.estimated_arrival_time and self.estimated_arrival_time <= self.departure_time:
            raise ValueError("estimated_arrival_time must be after departure_time")
        return self


class RideActionRequest(CancelBookingRequest):
    pass


class RiderBookingItem(BookingResponse):
    rider_name: str | None = None
    rider_photo_url: str | None = None


class RideBookingListResponse(BaseModel):
    items: list[RiderBookingItem]
    next_cursor: str | None = None


class ExpireRequestsResponse(BaseModel):
    expired: int
