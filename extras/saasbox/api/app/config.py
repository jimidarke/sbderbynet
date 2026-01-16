"""
Application configuration loaded from environment variables.
"""
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Application
    app_name: str = "SoapboxDerbyNet API"
    app_version: str = "1.0.0"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    api_v1_prefix: str = "/v1"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    cors_origins: list[str] = [
        "https://soapboxderbynet.com",
        "https://www.soapboxderbynet.com",
        "http://localhost:3000",
        "http://localhost:8080",
    ]

    # Database (PostgreSQL)
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/soapboxderbynet"
    database_pool_size: int = 5
    database_max_overflow: int = 10
    database_pool_timeout: int = 30

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_cache_ttl: int = 1  # seconds for active race data

    # JWT
    jwt_secret_key: str = "CHANGE-ME-IN-PRODUCTION-USE-STRONG-SECRET"
    jwt_algorithm: str = "RS256"
    jwt_access_token_expire_minutes: int = 15
    jwt_refresh_token_expire_days: int = 30
    jwt_issuer: str = "soapboxderbynet.com"

    # Firebase
    firebase_project_id: str = ""
    firebase_credentials_path: str = ""

    # FCM Push Notifications (per FCM_NOTIFICATION_PLAN.md)
    fcm_enabled: bool = True
    fcm_staging_lookahead_heats: int = 5  # Notify when favorite within N heats
    fcm_dedup_window_seconds: int = 300   # 5 minute deduplication window
    fcm_batch_size: int = 500             # FCM multicast limit
    fcm_notification_log_retention_days: int = 30

    # Alert Manager (logging)
    alert_manager_url: str = "https://alert.d-t.pw/alert"
    alert_manager_username: str = "soapboxderbynet"
    alert_manager_password: str = ""
    alert_manager_enabled: bool = True

    # Stripe (donations)
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_publishable_key: str = ""

    # Rate Limiting
    rate_limit_user_per_minute: int = 100
    rate_limit_device_per_minute: int = 1000
    rate_limit_auth_per_minute: int = 20

    # Security
    device_signature_max_age_seconds: int = 300  # 5 minutes
    nonce_cache_ttl_seconds: int = 600  # 10 minutes

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        return self.environment == "development"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
