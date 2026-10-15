import enum
from datetime import date, datetime

from sqlalchemy import Date, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.db.types import DateTime3, UnsignedBigInt, now_ms, now_ms_on_update
from app.models.user import MYSQL_TABLE_ARGS, enum_values


class Gender(str, enum.Enum):
    male = "male"
    female = "female"
    other = "other"
    prefer_not_to_say = "prefer_not_to_say"


class UserProfile(Base):
    __tablename__ = "user_profile"
    __table_args__ = MYSQL_TABLE_ARGS

    id_user: Mapped[int] = mapped_column(  # 1:1 with user
        UnsignedBigInt, ForeignKey("user.id_user", name="fk_user_profile_user"), primary_key=True, autoincrement=False
    )
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    photo_url: Mapped[str | None] = mapped_column(String(500))
    about: Mapped[str | None] = mapped_column(String(500))
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    gender: Mapped[Gender | None] = mapped_column(Enum(Gender, values_callable=enum_values, name="gender"))
    created_at: Mapped[datetime] = mapped_column(DateTime3, nullable=False, server_default=now_ms())
    updated_at: Mapped[datetime] = mapped_column(DateTime3, nullable=False, server_default=now_ms_on_update())

    user: Mapped["User"] = relationship(back_populates="profile")
