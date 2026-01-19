"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    DATABASE_URL: str = "sqlite:///./cycling_trainer.db"

    # Strava OAuth
    STRAVA_CLIENT_ID: str = ""
    STRAVA_CLIENT_SECRET: str = ""
    STRAVA_REDIRECT_URI: str = "http://localhost:5173/auth/callback"

    # JWT Authentication
    JWT_SECRET_KEY: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Google Gemini AI
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-1.5-flash"  # gemini-1.5-flash or gemini-1.5-pro

    # Aliases for compatibility with auth_service
    @property
    def SECRET_KEY(self) -> str:
        return self.JWT_SECRET_KEY

    @property
    def ALGORITHM(self) -> str:
        return self.JWT_ALGORITHM

    @property
    def ACCESS_TOKEN_EXPIRE_MINUTES(self) -> int:
        return self.JWT_ACCESS_TOKEN_EXPIRE_MINUTES

    # Frontend URL for CORS
    FRONTEND_URL: str = "http://localhost:5173"

    # Strava API URLs
    STRAVA_AUTH_URL: str = "https://www.strava.com/oauth/authorize"
    STRAVA_TOKEN_URL: str = "https://www.strava.com/oauth/token"
    STRAVA_API_URL: str = "https://www.strava.com/api/v3"
    STRAVA_API_BASE_URL: str = "https://www.strava.com/api/v3"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Create a global settings instance for direct import
settings = get_settings()
