from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings for WebSocket chat application."""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False)

    table_name: str
    aws_region: str = "us-east-1"
    # Optional config for LocalStack/testing
    dynamodb_endpoint_url: Optional[str] = None


settings = Settings()
