import os
from functools import lru_cache
from typing import List


class ProductionConfig:
    """Production defaults and validation helpers."""

    # URLs
    FRONTEND_URL = "https://land-ten-mvp-3-0.vercel.app"
    BACKEND_URL = "https://landtenmvp3-55ce0053f28a.herokuapp.com"

    # AWS
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
    DYNAMODB_ENDPOINT = None  # Always real AWS for production
    S3_INCIDENT_BUCKET = "landten-incident-photos-prod"
    S3_COMPLETION_BUCKET = "landten-job-completion-photos-prod"

    # Stripe
    STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
    STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
    STRIPE_CONNECT_CLIENT_ID = os.getenv("STRIPE_CONNECT_CLIENT_ID")
    PLATFORM_FEE_PERCENTAGE = 15

    # CORS
    ALLOWED_ORIGINS: List[str] = [
        "https://land-ten-mvp-3-0.vercel.app",
        "https://landtenmvp3-55ce0053f28a.herokuapp.com",
    ]

    # Feature flags
    ENABLE_STREAM_CHAT = os.getenv("STREAM_API_KEY") is not None
    ENABLE_EMAIL_NOTIFICATIONS = True

    @classmethod
    def validate(cls):
        """Fail fast if required environment variables are missing."""
        required = [
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "STRIPE_SECRET_KEY",
            "STRIPE_WEBHOOK_SECRET",
        ]
        missing = [var for var in required if not os.getenv(var)]
        if missing:
            raise ValueError(f"Missing required env vars: {missing}")


@lru_cache()
def get_config() -> ProductionConfig:
    return ProductionConfig()
