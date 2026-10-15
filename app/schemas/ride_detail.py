import enum
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.ride_booking import BookingStatus
from app.schemas.my_ride import RideInfo, RideRequestsInfo


class RideRole(str, enum.Enum):
    driver = "driver"  # I offered this ride
    rider = "rider"  # I have (or had) a booking on it
    viewer = "viewer"  # neither


class RiderInfo(BaseModel):
    id_user: str  # string: snowflake IDs exceed JS safe-integer range
    full_name: str | None
    photo_url: str | None


class BookingBrief(BaseModel):
    id_booking: str
    status: BookingStatus
    seats_booked: int
    price_per_seat: Decimal  # snapshot at booking time
    total_amount: Decimal
    rider_note: str | None
    created_at: datetime  # UTC


class RideBookingInfo(BookingBrief):
    """Driver view: a passenger or pending request."""

    rider: RiderInfo


class RideDetailResponse(RideInfo):
    role: RideRole
    my_booking: BookingBrief | None  # my active booking, else my most recent one; null if I never booked
    requests: RideRequestsInfo | None  # driver only
    bookings: list[RideBookingInfo] | None  # driver only: active (requested or accepted) bookings, oldest first
