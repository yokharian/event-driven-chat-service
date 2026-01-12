from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # DynamoDB configuration
    conversations_table_name: str = "conversations"
    messages_table_name: str = "messages"
    channels_table_name: str = "channels"
    chat_events_table_name: str = "chat_events"
    connections_table_name: str = "connections"

    # DynamoDB endpoint (for LocalStack)
    dynamodb_endpoint_url: Optional[str] = None

    # AWS region
    aws_region: str = "us-east-1"

    # Powertools configuration
    debug: Optional[bool] = False

    # API Gateway WebSocket endpoint (for delivery worker)
    websocket_api_endpoint: Optional[str] = None

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
