from datetime import datetime

from sqlalchemy import CHAR, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.db.types import DateTime3, UnsignedBigInt, now_ms
from app.models.user import MYSQL_TABLE_ARGS


class UserSession(Base):
    """One row per refresh token. Access JWTs are verified by signature only and never touch this table."""

    __tablename__ = "user_session"
    __table_args__ = (
        UniqueConstraint("refresh_token_hash", name="uk_session_refresh_token"),
        Index("idx_session_user", "id_user"),
        MYSQL_TABLE_ARGS,
    )

    id_session: Mapped[int] = mapped_column(UnsignedBigInt, primary_key=True, autoincrement=False)  # app-generated
    id_user: Mapped[int] = mapped_column(
        UnsignedBigInt, ForeignKey("user.id_user", name="fk_user_session_user"), nullable=False
    )
    refresh_token_hash: Mapped[str] = mapped_column(CHAR(64), nullable=False)  # SHA-256 hex of the refresh token
    expires_at: Mapped[datetime] = mapped_column(DateTime3, nullable=False)  # UTC
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime3)  # NULL = active
    created_at: Mapped[datetime] = mapped_column(DateTime3, nullable=False, server_default=now_ms())
