import enum
from datetime import datetime

from sqlalchemy import Enum, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.db.session import Base
from app.db.types import DateTime3, UnsignedBigInt, now_ms, now_ms_on_update

MYSQL_TABLE_ARGS = {
    "mysql_engine": "InnoDB",
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_0900_ai_ci",
}


def enum_values(e: type[enum.Enum]) -> list[str]:
    return [m.value for m in e]


class UserStatus(str, enum.Enum):
    active = "active"
    blocked = "blocked"
    deleted = "deleted"


class User(Base):
    __tablename__ = "user"
    __table_args__ = (
        UniqueConstraint("user_name", name="uk_user_user_name"),
        UniqueConstraint("email", name="uk_user_email"),
        UniqueConstraint("phone_number", name="uk_user_phone_number"),
        MYSQL_TABLE_ARGS,
    )

    id_user: Mapped[int] = mapped_column(UnsignedBigInt, primary_key=True, autoincrement=False)  # app-generated
    user_name: Mapped[str | None] = mapped_column(String(50))  # optional; stored lowercase
    email: Mapped[str | None] = mapped_column(String(255))
    phone_number: Mapped[str | None] = mapped_column(String(20))  # E.164
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[UserStatus] = mapped_column(
        Enum(UserStatus, values_callable=enum_values, name="user_status"),
        nullable=False,
        default=UserStatus.active,
        server_default=UserStatus.active.value,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime3, nullable=False, server_default=now_ms())
    updated_at: Mapped[datetime] = mapped_column(DateTime3, nullable=False, server_default=now_ms_on_update())
    last_active: Mapped[datetime | None] = mapped_column(DateTime3)  # update throttled, not per request

    profile: Mapped["UserProfile | None"] = relationship(back_populates="user", uselist=False, passive_deletes="all")
    documents: Mapped[list["UserDocument"]] = relationship(back_populates="user", passive_deletes="all")
    vehicles: Mapped[list["Vehicle"]] = relationship(back_populates="user", passive_deletes="all")

    @validates("user_name")
    def _lower_user_name(self, _key: str, value: str | None) -> str | None:
        return value.strip().lower() if value is not None else None
