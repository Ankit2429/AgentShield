import os
import sys

class Settings:
    APP_ENV: str = os.getenv("APP_ENV", "development")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./agentshield.db")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

settings = Settings()

# Secure startup check: reject default secrets in production environment
if settings.APP_ENV == "production":
    if settings.SECRET_KEY == "dev-secret-key-change-in-production":
        print("[CRITICAL] SECRET_KEY cannot be set to default value in production!", file=sys.stderr)
        sys.exit(1)
