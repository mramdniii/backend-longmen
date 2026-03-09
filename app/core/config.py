from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    DATABASE_URL: str
    DATABASE_URL_SYNC: str

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Security
    MAX_FAILED_LOGIN_ATTEMPTS: int = 3
    ACCOUNT_LOCK_DURATION_MINUTES: int = 30
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 60

    # App
    APP_ENV: str = "development"
    APP_NAME: str = "AuthService"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
