from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.notification import NotificationType


class NotificationItem(BaseModel):
    idNotification: str  # string: snowflake IDs exceed JS safe-integer range
    type: NotificationType
    idRide: str
    idBooking: str | None
    message: str
    createdAt: datetime  # UTC

    @field_validator("idNotification", "idRide", "idBooking", mode="before")
    @classmethod
    def serialize_large_ids(cls, value):
        return None if value is None else str(value)

    @field_validator("createdAt")
    @classmethod
    def utc_datetime(cls, value):
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class NotificationListResponse(BaseModel):
    items: list[NotificationItem]  # unread only, newest first
    unreadCount: int  # total unread, may exceed len(items)


class MarkAllReadResponse(BaseModel):
    marked: int


class SendNotificationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    idUser: int = Field(gt=0, le=2**64 - 1, description="Recipient; must be the ride's driver or a rider who booked it. Send large IDs as strings.")
    type: NotificationType
    idRide: int = Field(gt=0, le=2**64 - 1)
    idBooking: int | None = Field(default=None, gt=0, le=2**64 - 1, description="Must belong to idRide when given.")
    message: str = Field(min_length=1, max_length=255)

    @field_validator("idUser", "idRide", "idBooking", mode="before")
    @classmethod
    def reject_boolean_ids(cls, value):
        if isinstance(value, bool):
            raise ValueError("IDs must be positive integers")
        return value

    @field_validator("message")
    @classmethod
    def strip_message(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("message must not be blank")
        return value
