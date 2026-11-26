from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "postgresql+psycopg://alauto_app:alauto@db:5432/alauto"
    jwt_secret: str = "development-only-change-me"
    jwt_expire_minutes: int = 480
    cors_origins: str = "http://localhost:8080"
    initial_admin_login: str = "admin"
    initial_admin_password: str = "change-me"

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()

