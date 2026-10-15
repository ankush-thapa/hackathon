from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Hopr"
    DATABASE_URL: str = "mysql+mysqlconnector://user:password@localhost:3306/hackathon"
    MEDIA_DIR: Path = Path(__file__).resolve().parents[2] / "media"  # uploaded files live in <repo>/media
    MEDIA_BASE_URL: str | None = None  # public base for media URLs, e.g. https://api.example.com; defaults to the request host
    DOCUMENT_DIR: Path = Path(__file__).resolve().parents[2] / "private_documents"
    MAX_UPLOAD_BYTES: int = 5 * 1024 * 1024
    JWT_SECRET: str = "dev-only-insecure-secret-change-me-in-env"  # set 32+ random bytes outside local dev
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30  # also the session's maximum lifetime

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
