from datetime import datetime, timezone
from pydantic import BaseModel, field_validator
from app.models.user_document import DocType


class DocumentResponse(BaseModel):
    id_user_doc: str
    id_user: str
    doc_type: DocType
    doc_number: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    download_url: str

    @field_validator("id_user_doc", "id_user", mode="before")
    @classmethod
    def ids(cls, value):
        return str(value)

    @field_validator("created_at", "updated_at")
    @classmethod
    def utc(cls, value):
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


class DocumentListResponse(BaseModel):
    items: list[DocumentResponse]
    next_cursor: str | None = None
