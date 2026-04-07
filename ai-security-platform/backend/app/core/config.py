from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_name: str = "SecureAI Monitor"
    environment: str = "development"
    debug: bool = False
    allowed_origins: str = "http://localhost:3000"

    # Database
    database_url: str

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # AI Engine
    anomaly_threshold: float = 0.65
    model_retrain_interval_hours: int = 24
    embedding_model: str = "all-MiniLM-L6-v2"
    embedding_dim: int = 384

    # Alerts
    alert_webhook_url: str = ""
    alert_email: str = ""

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
