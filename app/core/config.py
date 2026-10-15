from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "hackathon"
    DATABASE_URL: str = "mysql+mysqlconnector://user:password@localhost:3306/hackathon"
    MEDIA_DIR: Path = Path(__file__).resolve().parents[2] / "media"  # uploaded files live in <repo>/media
    MEDIA_BASE_URL: str | None = None  # public base for media URLs, e.g. https://api.example.com; defaults to the request host
    MAX_UPLOAD_BYTES: int = 5 * 1024 * 1024

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
