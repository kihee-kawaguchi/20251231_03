"""Unit tests for configuration module."""

import pytest
from pydantic import ValidationError

from src.core.config import Settings


@pytest.mark.unit
class TestSettings:
    """Test configuration settings."""

    def test_settings_load_from_env(self, setup_test_env):
        """Test loading settings from environment variables."""
        settings = Settings()

        assert settings.env == "test"
        assert settings.chatwork_api_token == "test_chatwork_token"
        assert settings.lark_app_id == "cli_test"
        assert settings.lark_app_secret == "test_lark_secret"
        assert settings.redis_url == "redis://localhost:6379/0"
        assert settings.log_level == "DEBUG"
        assert settings.enable_loop_detection is True

    def test_settings_defaults(self, setup_test_env):
        """Test default configuration values."""
        settings = Settings()

        assert settings.host == "0.0.0.0"
        assert settings.port == 8000
        assert settings.debug is True  # Default is True in development
        assert settings.max_message_length == 4000
        assert settings.message_ttl_seconds == 86400
        assert settings.max_retry_attempts == 5

    def test_message_prefix_settings(self, setup_test_env):
        """Test message prefix configuration."""
        settings = Settings()

        assert settings.message_prefix_chatwork == "[From Chatwork]"
        assert settings.message_prefix_lark == "[From Lark]"

    def test_retry_settings(self, setup_test_env):
        """Test retry configuration."""
        settings = Settings()

        assert settings.max_retry_attempts == 5
        assert settings.retry_min_wait_seconds == 2  # Default is 2 seconds
        assert settings.retry_max_wait_seconds == 60

    def test_env_override(self, monkeypatch):
        """Test environment variable override of defaults."""
        # Override default values with environment variables
        monkeypatch.setenv("CHATWORK_API_TOKEN", "custom_token")
        monkeypatch.setenv("LARK_APP_ID", "cli_custom")

        settings = Settings()
        assert settings.chatwork_api_token == "custom_token"
        assert settings.lark_app_id == "cli_custom"

    def test_log_level_validation(self, monkeypatch, setup_test_env):
        """Test log level validation."""
        monkeypatch.setenv("LOG_LEVEL", "INFO")
        settings = Settings()
        assert settings.log_level == "INFO"

        monkeypatch.setenv("LOG_LEVEL", "ERROR")
        settings = Settings()
        assert settings.log_level == "ERROR"
