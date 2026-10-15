from datetime import datetime, timezone

from pydantic import BaseModel, field_validator


class StationResponse(BaseModel):
    id_station: int
    station_name: str
    is_active: bool
    created_at: datetime

    @field_validator("created_at")
    @classmethod
    def utc_datetime(cls, value):
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class StationListResponse(BaseModel):
    items: list[StationResponse]
    total: int
    limit: int
    offset: int
