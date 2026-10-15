import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Enum, ForeignKey, Index, Numeric, String, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.db.types import DateTime3, UnsignedBigInt, UnsignedInt, UnsignedTinyInt, now_ms, now_ms_on_update
from app.models.user import MYSQL_TABLE_ARGS, enum_values


class RideStatus(str, enum.Enum):
    open = "open"
    full = "full"
    started = "started"
    completed = "completed"
    cancelled = "cancelled"


class Ride(Base):
    """Ride offered by a driver. id_driver / id_vehicle are not FK-constrained."""

    __tablename__ = "ride"
    __table_args__ = (
        Index("idx_ride_search", "id_source_station", "id_destination_station", "status", "departure_time"),
        Index("idx_ride_driver_departure", "id_driver", "departure_time"),
        Index("idx_ride_vehicle_departure", "id_vehicle", "departure_time"),
        Index("idx_ride_status_departure", "status", "departure_time"),
        CheckConstraint("id_source_station <> id_destination_station", name="chk_ride_diff_stations"),
        CheckConstraint("total_seats BETWEEN 1 AND 8", name="chk_ride_total_seats"),
        CheckConstraint("available_seats <= total_seats", name="chk_ride_available_seats"),
        CheckConstraint("price_per_seat >= 0", name="chk_ride_price"),
        MYSQL_TABLE_ARGS,
    )

    id_ride: Mapped[int] = mapped_column(UnsignedBigInt, primary_key=True, autoincrement=False)  # app-generated
    id_driver: Mapped[int] = mapped_column(UnsignedBigInt, nullable=False)  # id_user of the driver
    id_vehicle: Mapped[int] = mapped_column(UnsignedBigInt, nullable=False)
    id_source_station: Mapped[int] = mapped_column(
        UnsignedInt, ForeignKey("station.id_station", name="fk_ride_source_station"), nullable=False
    )
    id_destination_station: Mapped[int] = mapped_column(
        UnsignedInt, ForeignKey("station.id_station", name="fk_ride_destination_station"), nullable=False
    )
    departure_time: Mapped[datetime] = mapped_column(DateTime3, nullable=False)  # UTC
    estimated_arrival_time: Mapped[datetime | None] = mapped_column(DateTime3)
    total_seats: Mapped[int] = mapped_column(UnsignedTinyInt, nullable=False)
    available_seats: Mapped[int] = mapped_column(UnsignedTinyInt, nullable=False)
    price_per_seat: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=Decimal("0.00"), server_default=text("0.00")
    )
    notes: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[RideStatus] = mapped_column(
        Enum(RideStatus, values_callable=enum_values, name="ride_status"),
        nullable=False,
        default=RideStatus.open,
        server_default=RideStatus.open.value,
    )
    cancel_reason: Mapped[str | None] = mapped_column(String(255))
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime3)
    version: Mapped[int] = mapped_column(UnsignedInt, nullable=False, server_default=text("1"))
    created_at: Mapped[datetime] = mapped_column(DateTime3, nullable=False, server_default=now_ms())
    updated_at: Mapped[datetime] = mapped_column(DateTime3, nullable=False, server_default=now_ms_on_update())

    # ORM updates bump `version` and raise StaleDataError if another writer got there first.
    __mapper_args__ = {"version_id_col": version}

    source_station: Mapped["Station"] = relationship(foreign_keys=[id_source_station])
    destination_station: Mapped["Station"] = relationship(foreign_keys=[id_destination_station])
    bookings: Mapped[list["RideBooking"]] = relationship(back_populates="ride", passive_deletes="all")
