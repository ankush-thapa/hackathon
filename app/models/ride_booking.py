import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, Computed, Enum, ForeignKey, Index, Numeric, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.db.types import DateTime3, TinyInt, UnsignedBigInt, UnsignedInt, UnsignedTinyInt, now_ms, now_ms_on_update
from app.models.user import MYSQL_TABLE_ARGS, enum_values

# CASE rather than MySQL's IF() so the same expression also works on SQLite in tests.
ACTIVE_FLAG_SQL = "CASE WHEN status IN ('requested', 'accepted') THEN 1 END"


class BookingStatus(str, enum.Enum):
    requested = "requested"
    accepted = "accepted"
    rejected = "rejected"
    cancelled_by_rider = "cancelled_by_rider"
    cancelled_by_driver = "cancelled_by_driver"
    expired = "expired"
    completed = "completed"


class RideBooking(Base):
    """Booking by a rider on a ride. id_rider / id_driver are not FK-constrained."""

    __tablename__ = "ride_booking"
    __table_args__ = (
        # active_flag is NULL once inactive, so only one requested/accepted booking per rider per ride.
        UniqueConstraint("id_ride", "id_rider", "active_flag", name="uk_booking_one_active"),
        Index("idx_booking_ride_status", "id_ride", "status"),
        Index("idx_booking_rider_created", "id_rider", "created_at"),
        Index("idx_booking_driver_status", "id_driver", "status", "created_at"),
        CheckConstraint("seats_booked BETWEEN 1 AND 8", name="chk_booking_seats"),
        CheckConstraint("total_amount >= 0", name="chk_booking_amount"),
        MYSQL_TABLE_ARGS,
    )

    id_booking: Mapped[int] = mapped_column(UnsignedBigInt, primary_key=True, autoincrement=False)  # app-generated
    id_ride: Mapped[int] = mapped_column(
        UnsignedBigInt, ForeignKey("ride.id_ride", name="fk_booking_ride"), nullable=False
    )
    id_rider: Mapped[int] = mapped_column(UnsignedBigInt, nullable=False)  # id_user of the rider
    id_driver: Mapped[int] = mapped_column(UnsignedBigInt, nullable=False)  # copied from ride
    seats_booked: Mapped[int] = mapped_column(UnsignedTinyInt, nullable=False, default=1, server_default=text("1"))
    price_per_seat: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)  # snapshot at request time
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    rider_note: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[BookingStatus] = mapped_column(
        Enum(BookingStatus, values_callable=enum_values, name="booking_status"),
        nullable=False,
        default=BookingStatus.requested,
        server_default=BookingStatus.requested.value,
    )
    reject_reason: Mapped[str | None] = mapped_column(String(255))
    cancel_reason: Mapped[str | None] = mapped_column(String(255))
    responded_at: Mapped[datetime | None] = mapped_column(DateTime3)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime3)
    version: Mapped[int] = mapped_column(UnsignedInt, nullable=False, server_default=text("1"))
    created_at: Mapped[datetime] = mapped_column(DateTime3, nullable=False, server_default=now_ms())
    updated_at: Mapped[datetime] = mapped_column(DateTime3, nullable=False, server_default=now_ms_on_update())
    active_flag: Mapped[int | None] = mapped_column(TinyInt, Computed(ACTIVE_FLAG_SQL, persisted=True))

    # ORM updates bump `version` and raise StaleDataError if another writer got there first.
    __mapper_args__ = {"version_id_col": version}

    ride: Mapped["Ride"] = relationship(back_populates="bookings")
