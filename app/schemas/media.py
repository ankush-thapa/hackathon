from pydantic import BaseModel


class MediaUploadResponse(BaseModel):
    url: str  # pass this as `photoUrl` to POST /v1/auth/profile
    fileName: str
    contentType: str
    size: int
