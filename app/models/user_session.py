from datetime import datetime

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.db.types import DateTime3, UnsignedBigInt, now_ms, now_ms_on_update
from app.models.user import MYSQL_TABLE_ARGS


class UserSession(Base):
    """One row per login. The access token carries id_session as its `sid` claim."""

    __tablename__ = "user_session"
    __table_args__ = (
        Index("idx_user_session_user", "id_user", "revoked_at", "expires_at"),
        MYSQL_TABLE_ARGS,
    )

    id_session: Mapped[int] = mapped_column(UnsignedBigInt, primary_key=True, autoincrement=False)
    id_user: Mapped[int] = mapped_column(
        UnsignedBigInt, ForeignKey("user.id_user", name="fk_user_session_user"), nullable=False
    )
    user_agent: Mapped[str | None] = mapped_column(String(255))
    ip_address: Mapped[str | None] = mapped_column(String(45))  # fits IPv6
    expires_at: Mapped[datetime] = mapped_column(DateTime3, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime3)  # set on logout / remote revoke
    created_at: Mapped[datetime] = mapped_column(DateTime3, nullable=False, server_default=now_ms())
    updated_at: Mapped[datetime] = mapped_column(DateTime3, nullable=False, server_default=now_ms_on_update())

    user: Mapped["User"] = relationship(back_populates="sessions")
