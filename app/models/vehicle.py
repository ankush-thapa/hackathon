from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Enum,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import relationship, validates

from app.db.session import Base
from app.models.base import MYSQL_TABLE_OPTIONS, USER_ID_TYPE, TimestampMixin


class Vehicle(TimestampMixin, Base):
    __tablename__ = "vehicle"
    __table_args__ = (
        UniqueConstraint("registration_number", name="uk_vehicle_registration_number"),
        Index("idx_vehicle_user_status", "id_user", "status"),
        CheckConstraint(
            "seat_capacity BETWEEN 1 AND 8", name="chk_vehicle_seat_capacity"
        ),
        dict(MYSQL_TABLE_OPTIONS),
    )

    id_vehicle = Column(USER_ID_TYPE, primary_key=True, autoincrement=False)
    id_user = Column(
        USER_ID_TYPE,
        ForeignKey("user.id_user", name="fk_vehicle_user"),
        nullable=False,
    )
    make = Column(String(50), nullable=False)
    model = Column(String(50), nullable=False)
    color = Column(String(30), nullable=False)
    registration_number = Column(String(20), nullable=False)
    seat_capacity = Column(
        SmallInteger().with_variant(TINYINT(unsigned=True), "mysql"), nullable=False
    )
    vehicle_type = Column(
        Enum("car", "hatchback", "sedan", "suv", "bike", name="vehicle_type"),
        nullable=False,
        default="car",
        server_default="car",
    )
    car_photo = Column(String(500), nullable=True)  # photo URL from POST /v1/media/upload
    is_default = Column(
        Boolean().with_variant(TINYINT(display_width=1), "mysql"),
        nullable=False,
        default=False,
        server_default=text("0"),
    )
    status = Column(
        Enum("active", "inactive", "deleted", name="vehicle_status"),
        nullable=False,
        default="active",
        server_default="active",
    )

    user = relationship("User", back_populates="vehicles")

    @validates("registration_number")
    def _normalize_registration_number(self, key, value):
        return "".join(value.split()).upper()
