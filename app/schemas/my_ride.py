import enum
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel

from app.models.ride import RideStatus
from app.models.ride_booking import BookingStatus


class MyRideScope(str, enum.Enum):
    upcoming = "upcoming"  # still to happen (soonest first)
    past = "past"  # finished, cancelled, expired, or no longer active (most recent first)
    all = "all"  # everything (most recent first)


class StationInfo(BaseModel):
    id_station: int
    name: str


class DriverInfo(BaseModel):
    id_user: str  # string: snowflake IDs exceed JS safe-integer range
    full_name: str | None
    photo_url: str | None


class VehicleInfo(BaseModel):
    make: str
    model: str
    color: str
    vehicle_type: str


class RideInfo(BaseModel):
    id_ride: str
    status: RideStatus
    source: StationInfo
    destination: StationInfo
    departure_time: datetime  # UTC
    estimated_arrival_time: datetime | None
    total_seats: int
    available_seats: int
    price_per_seat: Decimal
    notes: str | None
    driver: DriverInfo
    vehicle: VehicleInfo | None


# ---- GET /v1/me/rides: rides I offered (driver) ----


class RideRequestsInfo(BaseModel):
    pending_requests: int
    accepted_seats: int


class MyRideItem(RideInfo):
    requests: RideRequestsInfo


class MyRidesResponse(BaseModel):
    items: list[MyRideItem]
    next_page: str | None
    prev_page: str | None


# ---- GET /v1/me/bookings: bookings I made (rider) ----


class MyBookingItem(BaseModel):
    id_booking: str
    status: BookingStatus
    seats_booked: int
    price_per_seat: Decimal  # snapshot at booking time
    total_amount: Decimal
    rider_note: str | None
    created_at: datetime  # UTC
    ride: RideInfo


class MyBookingsResponse(BaseModel):
    items: list[MyBookingItem]
    next_page: str | None
    prev_page: str | None
