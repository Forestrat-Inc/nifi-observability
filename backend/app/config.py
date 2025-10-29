"""Application configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # NiFi Configuration
    nifi_api_url: str = "https://localhost:8443/nifi-api/"
    nifi_username: str | None = None
    nifi_password: str | None = None
    
    # API Configuration
    api_title: str = "NiFi Observability API"
    api_description: str = "REST API for monitoring and visualizing Apache NiFi process groups"
    api_version: str = "0.1.0"
    
    # CORS Configuration
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:3001"]
    
    # Request Configuration
    request_timeout: int = 30
    
    class Config:
        """Pydantic configuration."""
        env_file = ".env"
        case_sensitive = False


settings = Settings()

