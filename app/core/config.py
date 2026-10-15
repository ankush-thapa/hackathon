from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "hackathon"
    DATABASE_URL: str = "mysql+mysqlconnector://user:password@localhost:3306/hackathon"
    JWT_SECRET: str = "dev-only-insecure-secret-change-me-in-env"  # set 32+ random bytes outside local dev
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
