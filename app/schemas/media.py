from pydantic import BaseModel


class MediaUploadResponse(BaseModel):
    url: str  # pass as `photoUrl` to POST /v1/auth/profile or `photo_url` to POST /v1/vehicles
    fileName: str
    contentType: str
    size: int
