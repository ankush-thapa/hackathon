from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, status

from app.api.deps import get_current_user_id
from app.core.config import settings
from app.schemas.media import MediaUploadResponse
from app.services.media_service import FileTooLargeError, MediaService, UnsupportedMediaError

router = APIRouter(prefix="/v1/media", tags=["media"])

MEDIA_URL_PATH = "/media"  # where main.py serves settings.MEDIA_DIR


def get_media_service() -> MediaService:
    return MediaService(Path(settings.MEDIA_DIR), settings.MAX_UPLOAD_BYTES)


@router.post("/upload", response_model=MediaUploadResponse, status_code=status.HTTP_201_CREATED)
def upload_media(request: Request, file: UploadFile, current_user_id: int = Depends(get_current_user_id), service: MediaService = Depends(get_media_service)):
    """Store an image (JPEG, PNG or WebP, up to 5 MB) in the media folder and return its public URL."""
    try:
        saved = service.save_image(file.file)
    except UnsupportedMediaError:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="only JPEG, PNG or WebP images are allowed")
    except FileTooLargeError:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=f"file exceeds {settings.MAX_UPLOAD_BYTES} bytes"
        )
    base = (settings.MEDIA_BASE_URL or str(request.base_url)).rstrip("/")
    return MediaUploadResponse(url=f"{base}{MEDIA_URL_PATH}/{saved['fileName']}", **saved)
