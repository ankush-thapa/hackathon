from sqlalchemy import Column, Enum, String, UniqueConstraint
from sqlalchemy.orm import relationship, validates

from app.db.session import Base
from app.models.base import (
    DATETIME_MILLISECONDS,
    MYSQL_TABLE_OPTIONS,
    USER_ID_TYPE,
    TimestampMixin,
)


class User(TimestampMixin, Base):
    __tablename__ = "user"
    __table_args__ = (
        UniqueConstraint("user_name", name="uk_user_user_name"),
        UniqueConstraint("email", name="uk_user_email"),
        UniqueConstraint("phone_number", name="uk_user_phone_number"),
        dict(MYSQL_TABLE_OPTIONS),
    )

    id_user = Column(USER_ID_TYPE, primary_key=True, autoincrement=False)
    user_name = Column(String(50), nullable=False)
    email = Column(String(255), nullable=True)
    phone_number = Column(String(20), nullable=True)
    password_hash = Column(String(255), nullable=False)
    status = Column(
        Enum("active", "blocked", "deleted", name="user_status"),
        nullable=False,
        default="active",
        server_default="active",
    )
    last_active = Column(DATETIME_MILLISECONDS, nullable=True)

    profile = relationship(
        "UserProfile", back_populates="user", uselist=False, passive_deletes="all"
    )
    documents = relationship("UserDocument", back_populates="user", passive_deletes="all")
    vehicles = relationship("Vehicle", back_populates="user", passive_deletes="all")

    @validates("user_name")
    def _normalize_user_name(self, key, value):
        return value.lower()
