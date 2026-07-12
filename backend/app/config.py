from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql://reverse_hh:reverse_hh@localhost:5432/reverse_hh"
    jwt_secret: str = "change-me-in-production"
    jwt_expire_hours: int = 24
    cookie_name: str = "access_token"
    debug: bool = True
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    frontend_dir: str = ""


settings = Settings()


def get_frontend_path() -> Path:
    if settings.frontend_dir:
        return Path(settings.frontend_dir)
    return Path(__file__).resolve().parent.parent.parent / "frontend"
