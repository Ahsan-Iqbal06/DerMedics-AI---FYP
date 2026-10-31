from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", extra="ignore")

    app_name: str = "DerMedics AI"
    database_url: str = f"sqlite:///{BASE_DIR / 'dermedics.db'}"
    auto_create_tables: bool = True

    jwt_secret: str = "change-me-to-a-long-random-string"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 15
    refresh_token_days: int = 7

    model_path: str = ""
    labels_path: str = ""
    confidence_threshold: float = 0.6
    max_upload_mb: int = 10

    llm_base_url: str = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"
    llm_api_key: str = ""
    llm_model: str = "qwen-plus"
    # Comma-separated models tried in order when the main one fails (e.g. out of credits or rate-limited).
    llm_fallback_models: str = ""
    # Reasoning models "think" before answering (~20 s per call); off by default for a responsive app.
    llm_disable_reasoning: bool = True

    google_places_key: str = ""

    # Email for password-reset codes. Leave smtp_host empty in development: codes are written to the server log.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = ""
    smtp_use_tls: bool = True
    password_reset_minutes: int = 15

    cors_origins: str = "*"
    upload_dir: Path = BASE_DIR / "uploads"
    data_dir: Path = BASE_DIR / "app" / "data"


@lru_cache
def get_settings() -> Settings:
    return Settings()
