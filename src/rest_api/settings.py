from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    # DynamoDB configuration
    channels_table_name: str = "channels"
    chat_events_table_name: str = "chat_events"
    connections_table_name: str = "connections"

    # Powertools configuration
    debug: Optional[bool] = False

    # API Gateway WebSocket endpoint (for delivery worker)
    websocket_api_endpoint: Optional[str] = None


settings = Settings()
