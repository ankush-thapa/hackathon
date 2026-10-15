from sqlalchemy import Boolean, Column, Enum, ForeignKey, Index, String, text
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import relationship

from app.db.session import Base
from app.models.base import MYSQL_TABLE_OPTIONS, USER_ID_TYPE, TimestampMixin


class UserDocument(TimestampMixin, Base):
    __tablename__ = "user_documents"
    __table_args__ = (
        Index("idx_user_documents_user_type", "id_user", "doc_type", "is_active"),
        Index("idx_user_documents_doc_number", "doc_type", "doc_number"),
        dict(MYSQL_TABLE_OPTIONS),
    )

    id_user_doc = Column(USER_ID_TYPE, primary_key=True, autoincrement=False)
    id_user = Column(
        USER_ID_TYPE,
        ForeignKey("user.id_user", name="fk_user_documents_user"),
        nullable=False,
    )
    doc_type = Column(
        Enum("driving_license", "id_proof", "vehicle_rc", "insurance", name="user_doc_type"),
        nullable=False,
    )
    path = Column(String(500), nullable=False)
    doc_number = Column(String(50), nullable=False)
    is_active = Column(
        Boolean().with_variant(TINYINT(display_width=1), "mysql"),
        nullable=False,
        default=True,
        server_default=text("1"),
    )

    user = relationship("User", back_populates="documents")
