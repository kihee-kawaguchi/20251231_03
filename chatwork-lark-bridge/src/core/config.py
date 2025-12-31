"""Application configuration management."""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Environment
    env: str = "development"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True

    # Chatwork API
    chatwork_api_token: str = "test_token"  # Default for testing
    chatwork_webhook_secret: str = "dGVzdF9zZWNyZXQ="  # Default for testing
    chatwork_api_base_url: str = "https://api.chatwork.com/v2"

    # Lark API
    lark_app_id: str = "cli_test"  # Default for testing
    lark_app_secret: str = "test_secret"  # Default for testing
    lark_verification_token: str = "test_token"  # Default for testing
    lark_encrypt_key: Optional[str] = None
    lark_api_base_url: str = "https://open.larksuite.com/open-apis"

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_password: Optional[str] = None
    redis_max_connections: int = 10

    # Message Processing
    max_message_length: int = 4000
    message_ttl_seconds: int = 86400  # 24 hours
    enable_loop_detection: bool = True
    message_prefix_chatwork: str = "[From Chatwork]"
    message_prefix_lark: str = "[From Lark]"

    # Retry Configuration
    max_retry_attempts: int = 5
    retry_min_wait_seconds: int = 2
    retry_max_wait_seconds: int = 60

    # Rate Limiting
    chatwork_rate_limit_requests: int = 10
    chatwork_rate_limit_window_seconds: int = 10

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"  # json or text

    # Monitoring
    enable_metrics: bool = True
    metrics_port: int = 9090

    # Security
    allowed_ips_chatwork: Optional[str] = None
    allowed_ips_lark: Optional[str] = None

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.env == "production"

    @property
    def allowed_chatwork_ips(self) -> list[str]:
        """Parse allowed Chatwork IPs from comma-separated string."""
        if not self.allowed_ips_chatwork:
            return []
        return [ip.strip() for ip in self.allowed_ips_chatwork.split(",")]

    @property
    def allowed_lark_ips(self) -> list[str]:
        """Parse allowed Lark IPs from comma-separated string."""
        if not self.allowed_ips_lark:
            return []
        return [ip.strip() for ip in self.allowed_ips_lark.split(",")]


# Global settings instance
settings = Settings()
