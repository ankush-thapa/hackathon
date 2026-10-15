import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Path as ApiPath, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_id
from app.core.config import settings
from app.core.ids import new_id
from app.db.session import get_db
from app.models import UserDocument, DocType
from app.schemas.document import DocumentResponse, DocumentListResponse
from app.services.media_service import _detect_image

router = APIRouter(prefix="/v1/me/documents", tags=["documents"], responses={401: {"description": "Missing/invalid session"}, 404: {"description": "Document not found"}})
Id = Annotated[int, ApiPath(gt=0, le=2**64-1)]


def response(doc):
    return DocumentResponse(**{k: getattr(doc,k) for k in DocumentResponse.model_fields if k != "download_url"},
        download_url=f"/v1/me/documents/{doc.id_user_doc}/download")


def owned(db, user, doc_id):
    doc = db.get(UserDocument, doc_id)
    if doc is None or doc.id_user != user:
        raise HTTPException(404, "document not found")
    return doc


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def upload_document(doc_type: Annotated[DocType, Form()],
                    doc_number: Annotated[str, Form(min_length=1, max_length=50)],
                    file: Annotated[UploadFile, File(description="Private PDF, JPEG, PNG or WebP; maximum 5 MB.")],
                    user: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    """Multipart form: doc_type, doc_number, file. Files are private and never mounted under /media."""
    number = doc_number.strip()
    if not number:
        raise HTTPException(422, "doc_number must not be blank")
    directory = settings.DOCUMENT_DIR.resolve()
    media = settings.MEDIA_DIR.resolve()
    if directory == media or media in directory.parents:
        raise HTTPException(503, "DOCUMENT_DIR must be outside the public MEDIA_DIR")
    head = file.file.read(12)
    detected = ("pdf", "application/pdf") if head.startswith(b"%PDF-") else _detect_image(head)
    if detected is None:
        raise HTTPException(415, "document must be PDF, JPEG, PNG or WebP")
    directory.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}.{detected[0]}"
    destination = directory / name
    try:
        size = len(head)
        with destination.open("xb") as out:
            out.write(head)
            while chunk := file.file.read(65536):
                size += len(chunk)
                if size > settings.MAX_UPLOAD_BYTES:
                    raise HTTPException(413, "document exceeds maximum upload size")
                out.write(chunk)
        doc = UserDocument(id_user_doc=new_id(), id_user=user, doc_type=doc_type, path=name,
                           doc_number=number, is_active=True)
        db.add(doc)
        db.flush()
        db.refresh(doc)
        result = response(doc)
        db.commit()
        return result
    except Exception:
        db.rollback()
        destination.unlink(missing_ok=True)
        raise


@router.get("", response_model=DocumentListResponse)
def list_documents(doc_type: DocType | None = None, include_inactive: bool = False,
                   cursor: int | None = Query(default=None, gt=0, le=2**64-1),
                   limit: int = Query(default=20, ge=1, le=50),
                   user: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    query = select(UserDocument).where(UserDocument.id_user == user)
    if doc_type: query = query.where(UserDocument.doc_type == doc_type)
    if not include_inactive: query = query.where(UserDocument.is_active.is_(True))
    if cursor is not None: query = query.where(UserDocument.id_user_doc < cursor)
    docs = list(db.scalars(query.order_by(UserDocument.id_user_doc.desc()).limit(limit+1)))
    return DocumentListResponse(items=[response(d) for d in docs[:limit]],
        next_cursor=str(docs[limit-1].id_user_doc) if len(docs)>limit else None)


@router.get("/{id_document}/download", response_class=FileResponse)
def download_document(id_document: Id, user: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    doc = owned(db, user, id_document)
    if not doc.is_active:
        raise HTTPException(404, "document not found")
    directory = settings.DOCUMENT_DIR.resolve()
    path = (directory / doc.path).resolve()
    if path.parent != directory or not path.is_file():
        raise HTTPException(404, "document file not found")
    return FileResponse(path, filename=f"{doc.doc_type.value}{path.suffix}", headers={"Cache-Control": "no-store"})


@router.delete("/{id_document}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_document(id_document: Id, user: int = Depends(get_current_user_id), db: Session = Depends(get_db)):
    doc = owned(db, user, id_document)
    doc.is_active = False
    db.commit()
