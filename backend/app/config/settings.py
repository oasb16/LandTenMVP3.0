"""
Configuration settings for LandTenMVP3.0 backend.

This module centralizes all environment variable access and provides
typed configuration values with validation.
"""

import os
import logging
from typing import Optional


class Settings:
    """
    Centralized application settings loaded from environment variables.

    Usage:
        from app.config.settings import settings

        if settings.DEBUG_MODE:
            logger.debug("Debug message")
    """

    def __init__(self):
        """Initialize settings from environment variables."""
        # Load .env if available
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass

        # Debug & Logging
        self.DEBUG_MODE: bool = self._get_bool("DEBUG_MODE", False)
        self.LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO" if not self.DEBUG_MODE else "DEBUG")

        # Authentication
        self.AUTH_DISABLED: bool = self._get_bool("AUTH_DISABLED", True)
        self.USE_FIREBASE_ADMIN: bool = self._get_bool("USE_FIREBASE_ADMIN", False)

        # Backend URLs
        self.BACKEND_URL: Optional[str] = os.getenv("BACKEND_URL")
        self.BACKEND_INTERNAL_URL: Optional[str] = os.getenv("BACKEND_INTERNAL_URL", "http://localhost:8080")
        self.HEROKU_BACKEND_URL: Optional[str] = os.getenv("HEROKU_BACKEND_URL")
        self.DYNO: Optional[str] = os.getenv("DYNO")  # Heroku dyno identifier

        # CORS
        self.BACKEND_CORS_ORIGINS: str = os.getenv("BACKEND_CORS_ORIGINS", "*")

        # Pusher
        self.PUSHER_APP_ID: Optional[str] = os.getenv("PUSHER_APP_ID")
        self.PUSHER_KEY: Optional[str] = os.getenv("PUSHER_KEY")
        self.PUSHER_SECRET: Optional[str] = os.getenv("PUSHER_SECRET")
        self.PUSHER_CLUSTER: Optional[str] = os.getenv("PUSHER_CLUSTER", "us2")

        # OpenAI
        self.OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
        self.OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.OPENAI_TEMPERATURE: float = float(os.getenv("OPENAI_TEMPERATURE", "0.3"))
        self.AGENT_SYSTEM_PROMPT: str = os.getenv(
            "AGENT_SYSTEM_PROMPT",
            "You are LandTen's domain assistant. Infer issues, incidents, and actions intelligently."
        )

        # OpenAI Responses API (Migration to new architecture)
        self.LANDTEN_PROMPT_ID: Optional[str] = os.getenv("LANDTEN_PROMPT_ID")

        # Validate LANDTEN_PROMPT_ID for Responses API
        # Note: This validation is disabled by default to allow gradual migration
        # Enable by setting REQUIRE_PROMPT_ID=true in environment
        if os.getenv("REQUIRE_PROMPT_ID", "false").lower() == "true":
            if not self.LANDTEN_PROMPT_ID:
                raise ValueError(
                    "LANDTEN_PROMPT_ID environment variable not set. "
                    "Please create a unified prompt in OpenAI dashboard "
                    "(https://platform.openai.com/prompts) and set the prompt ID."
                )

        # Stream Chat
        self.STREAM_CHAT_API_KEY: Optional[str] = os.getenv("STREAM_CHAT_API_KEY")
        self.STREAM_CHAT_API_SECRET: Optional[str] = os.getenv("STREAM_CHAT_API_SECRET")
        self.STREAM_DEFAULT_CHANNEL: str = os.getenv("STREAM_DEFAULT_CHANNEL", "LandTenMVP3")
        self.STREAM_ALLOWED_ROLES: str = os.getenv("STREAM_ALLOWED_ROLES", "user,admin,guest,agent")
        self.STREAM_AGENT_USER_ID: str = os.getenv("STREAM_AGENT_USER_ID", "landten-agent")
        self.STREAM_AGENT_NAME: str = os.getenv("STREAM_AGENT_NAME", "LandTen Agent")
        self.STREAM_AGENT_AUTOJOIN: bool = self._get_bool("STREAM_AGENT_AUTOJOIN", True)
        self.STREAM_WEBHOOK_URL: Optional[str] = os.getenv("STREAM_WEBHOOK_URL")
        self.STREAM_WEBHOOK_SECRET: Optional[str] = os.getenv("STREAM_WEBHOOK_SECRET")

        # AWS
        self.AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
        self.AWS_ACCESS_KEY_ID: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID")
        self.AWS_SECRET_ACCESS_KEY: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY")
        self.MEDIA_BUCKET: Optional[str] = os.getenv("MEDIA_BUCKET")

        # DynamoDB Table Naming
        self.TABLE_PREFIX: str = os.getenv("TABLE_PREFIX", "landten")
        self.STAGE: str = os.getenv("STAGE", "dev")

        # Incident Thresholds
        self.INCIDENT_THRESHOLD_LOW: int = int(os.getenv("INCIDENT_THRESHOLD_LOW", "200"))
        self.INCIDENT_THRESHOLD_MEDIUM: int = int(os.getenv("INCIDENT_THRESHOLD_MEDIUM", "500"))
        self.INCIDENT_THRESHOLD_HIGH: int = int(os.getenv("INCIDENT_THRESHOLD_HIGH", "1000"))

        # Stripe
        self.STRIPE_SECRET_KEY: Optional[str] = os.getenv("STRIPE_SECRET_KEY")
        self.STRIPE_PUBLISHABLE_KEY: Optional[str] = os.getenv("STRIPE_PUBLISHABLE_KEY")
        self.STRIPE_WEBHOOK_SECRET: Optional[str] = os.getenv("STRIPE_WEBHOOK_SECRET")

        # Configure logging based on settings
        self._configure_logging()

    def _get_bool(self, key: str, default: bool = False) -> bool:
        """Parse boolean environment variable."""
        value = os.getenv(key, str(default)).lower()
        return value in ("true", "1", "yes", "on")

    def _configure_logging(self):
        """Configure Python logging based on settings."""
        log_level = getattr(logging, self.LOG_LEVEL.upper(), logging.INFO)

        # Configure root logger
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        if self.DEBUG_MODE:
            logging.info("[settings] DEBUG_MODE enabled - verbose logging active")

    def get_base_url(self) -> str:
        """Get the base URL for the backend."""
        if self.DYNO:
            return self.HEROKU_BACKEND_URL or self.BACKEND_URL or self.BACKEND_INTERNAL_URL
        return self.BACKEND_URL or self.BACKEND_INTERNAL_URL or "http://localhost:8080"


# Global settings instance
settings = Settings()


# Logging helper for conditional debug logging
class DebugLogger:
    """
    Helper class for conditional debug logging.

    Usage:
        from app.config.settings import debug_logger

        debug_logger.log("[incident-engine] Processing incident: %s", incident_id)
    """

    def __init__(self, settings_instance: Settings):
        self.settings = settings_instance
        self.logger = logging.getLogger("landten.debug")

    def log(self, message: str, *args, **kwargs):
        """Log debug message if DEBUG_MODE is enabled."""
        if self.settings.DEBUG_MODE:
            self.logger.debug(message, *args, **kwargs)

    def info(self, message: str, *args, **kwargs):
        """Log info message if DEBUG_MODE is enabled."""
        if self.settings.DEBUG_MODE:
            self.logger.info(message, *args, **kwargs)

    def warning(self, message: str, *args, **kwargs):
        """Log warning message (always, even without DEBUG_MODE)."""
        self.logger.warning(message, *args, **kwargs)

    def error(self, message: str, *args, **kwargs):
        """Log error message (always, even without DEBUG_MODE)."""
        self.logger.error(message, *args, **kwargs)


# Global debug logger instance
debug_logger = DebugLogger(settings)
