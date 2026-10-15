import enum
from datetime import datetime

from sqlalchemy import Boolean, Enum, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.db.types import DateTime3, UnsignedBigInt, now_ms
from app.models.user import MYSQL_TABLE_ARGS, enum_values


class NotificationType(str, enum.Enum):
    booking_requested = "booking_requested"
    booking_accepted = "booking_accepted"
    booking_rejected = "booking_rejected"
    booking_cancelled = "booking_cancelled"
    ride_cancelled = "ride_cancelled"
    ride_modified = "ride_modified"


class Notification(Base):
    """In-app notification for one user. id_user / id_ride / id_booking are not FK-constrained."""

    __tablename__ = "notification"
    __table_args__ = (
        Index("idx_notification_user", "id_user", "is_read", "created_at"),
        MYSQL_TABLE_ARGS,
    )

    id_notification: Mapped[int] = mapped_column(UnsignedBigInt, primary_key=True, autoincrement=False)  # app-generated
    id_user: Mapped[int] = mapped_column(UnsignedBigInt, nullable=False)  # recipient
    type: Mapped[NotificationType] = mapped_column(
        Enum(NotificationType, values_callable=enum_values, name="notification_type"), nullable=False
    )
    id_ride: Mapped[int] = mapped_column(UnsignedBigInt, nullable=False)
    id_booking: Mapped[int | None] = mapped_column(UnsignedBigInt)
    message: Mapped[str] = mapped_column(String(255), nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime3, nullable=False, server_default=now_ms())
