from sqlalchemy import Column, FetchedValue

from app.db.types import DateTime3, UnsignedBigInt, now_ms, now_ms_on_update

# Compatibility aliases shared by the vehicle model and existing imports.
USER_ID_TYPE = UnsignedBigInt
DATETIME_MILLISECONDS = DateTime3
MYSQL_TABLE_OPTIONS = {
    "mysql_engine": "InnoDB",
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_0900_ai_ci",
}


class TimestampMixin:
    created_at = Column(
        DateTime3, nullable=False, server_default=now_ms()
    )
    updated_at = Column(
        DateTime3,
        nullable=False,
        server_default=now_ms_on_update(),
        server_onupdate=FetchedValue(),
    )
