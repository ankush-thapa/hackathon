import enum
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Index, String, text
from sqlalchemy import Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.db.types import DateTime3, UnsignedBigInt, now_ms, now_ms_on_update
from app.models.user import MYSQL_TABLE_ARGS, enum_values


class DocType(str, enum.Enum):
    driving_license = "driving_license"
    id_proof = "id_proof"
    vehicle_rc = "vehicle_rc"
    insurance = "insurance"


class UserDocument(Base):
    __tablename__ = "user_documents"
    __table_args__ = (
        Index("idx_user_documents_user_type", "id_user", "doc_type", "is_active"),
        Index("idx_user_documents_doc_number", "doc_type", "doc_number"),
        MYSQL_TABLE_ARGS,
    )

    id_user_doc: Mapped[int] = mapped_column(UnsignedBigInt, primary_key=True, autoincrement=False)
    id_user: Mapped[int] = mapped_column(
        UnsignedBigInt, ForeignKey("user.id_user", name="fk_user_documents_user"), nullable=False
    )
    doc_type: Mapped[DocType] = mapped_column(
        Enum(DocType, values_callable=enum_values, name="doc_type"), nullable=False
    )
    path: Mapped[str] = mapped_column(String(500), nullable=False)  # object-storage key (private bucket)
    doc_number: Mapped[str] = mapped_column(String(50), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("1"))
    created_at: Mapped[datetime] = mapped_column(DateTime3, nullable=False, server_default=now_ms())
    updated_at: Mapped[datetime] = mapped_column(DateTime3, nullable=False, server_default=now_ms_on_update())

    user: Mapped["User"] = relationship(back_populates="documents")
