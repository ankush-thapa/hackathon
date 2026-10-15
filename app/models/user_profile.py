from sqlalchemy import Column, Date, Enum, ForeignKey, String
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.models.base import MYSQL_TABLE_OPTIONS, USER_ID_TYPE, TimestampMixin


class UserProfile(TimestampMixin, Base):
    __tablename__ = "user_profile"
    __table_args__ = dict(MYSQL_TABLE_OPTIONS)

    id_user = Column(
        USER_ID_TYPE,
        ForeignKey("user.id_user", name="fk_user_profile_user"),
        primary_key=True,
        autoincrement=False,
    )
    full_name = Column(String(100), nullable=False)
    photo_url = Column(String(500), nullable=True)
    about = Column(String(500), nullable=True)
    date_of_birth = Column(Date, nullable=True)
    gender = Column(
        Enum("male", "female", "other", "prefer_not_to_say", name="user_gender"),
        nullable=True,
    )

    user = relationship("User", back_populates="profile")
