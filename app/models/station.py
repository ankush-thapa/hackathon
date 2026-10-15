from datetime import datetime

from sqlalchemy import Boolean, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.db.types import DateTime3, UnsignedInt, now_ms
from app.models.user import MYSQL_TABLE_ARGS


class Station(Base):
    """Fixed list of pickup/drop-off points."""

    __tablename__ = "station"
    __table_args__ = (
        UniqueConstraint("station_name", name="uk_station_name"),
        MYSQL_TABLE_ARGS,
    )

    id_station: Mapped[int] = mapped_column(UnsignedInt, primary_key=True, autoincrement=True)
    station_name: Mapped[str] = mapped_column(String(100), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("1"))
    created_at: Mapped[datetime] = mapped_column(DateTime3, nullable=False, server_default=now_ms())
