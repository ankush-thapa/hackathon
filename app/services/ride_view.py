from datetime import datetime, timezone
from decimal import Decimal

from app.core.pagination import as_datetime
from app.schemas.my_ride import DriverInfo, StationInfo, VehicleInfo


def utc(v) -> datetime | None:
    return as_datetime(v).replace(tzinfo=timezone.utc) if v else None


def money(v) -> Decimal:
    return Decimal(str(v)).quantize(Decimal("0.01"))


def ride_fields(r: dict) -> dict:
    return dict(
        id_ride=str(r["id_ride"]),
        status=r["ride_status"],
        source=StationInfo(id_station=r["id_source_station"], name=r["source_station_name"]),
        destination=StationInfo(id_station=r["id_destination_station"], name=r["destination_station_name"]),
        departure_time=utc(r["departure_time"]),
        estimated_arrival_time=utc(r["estimated_arrival_time"]),
        total_seats=r["total_seats"],
        available_seats=r["available_seats"],
        price_per_seat=money(r["price_per_seat"]),
        notes=r["notes"],
        driver=DriverInfo(id_user=str(r["id_driver"]), full_name=r["driver_name"], photo_url=r["driver_photo_url"]),
        vehicle=VehicleInfo(
            make=r["vehicle_make"], model=r["vehicle_model"], color=r["vehicle_color"], vehicle_type=r["vehicle_type"]
        )
        if r["vehicle_make"]
        else None,
    )
