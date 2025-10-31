"""Application configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # NiFi Configuration
    nifi_api_url: str = "https://localhost:8443/nifi-api/"
    nifi_username: str | None = None
    nifi_password: str | None = None
    
    # Grafana/Loki Configuration
    grafana_url: str = "https://forestrat.grafana.net"
    grafana_api_key: str | None = None
    grafana_username: str | None = None
    grafana_password: str | None = None
    loki_datasource_uid: str | None = None  # Optional: Only needed if using Grafana datasource proxy
    loki_direct_url: str | None = None  # Optional: Direct Loki API URL (alternative to Grafana proxy)
    
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
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()

