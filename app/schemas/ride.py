from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class StationRef(BaseModel):
    idStation: int
    name: str


class DriverSummary(BaseModel):
    userId: str  # string: snowflake IDs exceed JS safe-integer range
    fullName: str | None
    photoUrl: str | None


class VehicleSummary(BaseModel):
    make: str
    model: str
    color: str
    vehicleType: str


class RideSummary(BaseModel):
    idRide: str
    source: StationRef
    destination: StationRef
    departureTime: datetime  # UTC
    estimatedArrivalTime: datetime | None
    totalSeats: int
    availableSeats: int
    pricePerSeat: Decimal
    notes: str | None
    driver: DriverSummary
    vehicle: VehicleSummary | None


class RideListResponse(BaseModel):
    items: list[RideSummary]
    next_page: str | None  # pass as `cursor` for the next page; null on the last page
    prev_page: str | None  # pass as `cursor` for the previous page; null on the first page
