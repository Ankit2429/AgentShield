import os
import sys

class Settings:
    APP_ENV: str = os.getenv("APP_ENV", "development")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./agentshield.db")
    
    # Secure SECRET_KEY loading
    _secret_key: str | None = os.getenv("SECRET_KEY")
    if not _secret_key:
        if APP_ENV == "production":
            print("[CRITICAL] SECRET_KEY environment variable is REQUIRED in production!", file=sys.stderr)
            sys.exit(1)
        else:
            print("[WARNING] SECRET_KEY environment variable is missing. Defaulting to development fallback key.", file=sys.stderr)
            SECRET_KEY: str = "dev-secret-key-change-in-production"
    else:
        if _secret_key == "dev-secret-key-change-in-production":
            if APP_ENV == "production":
                print("[CRITICAL] SECRET_KEY cannot be set to the default 'dev-secret-key-change-in-production' value in production!", file=sys.stderr)
                sys.exit(1)
            else:
                print("[WARNING] SECRET_KEY is set to the insecure default 'dev-secret-key-change-in-production' in development mode.", file=sys.stderr)
        SECRET_KEY: str = _secret_key

    DEMO_MODE: bool = os.getenv("DEMO_MODE", "false" if os.getenv("APP_ENV", "development") == "production" else "true").lower() in ("true", "1", "yes")

settings = Settings()
