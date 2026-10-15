from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Hopr"
    DATABASE_URL: str = "mysql+mysqlconnector://user:password@localhost:3306/hackathon"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
