from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Settings for WebSocket chat application."""
    
    table_name: str
    aws_region: str = "us-east-1"
    # Optional config for LocalStack/testing
    dynamodb_endpoint_url: Optional[str] = None


settings = Settings()
