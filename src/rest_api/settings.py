from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    # DynamoDB configuration
    channels_table_name: str = "channels"
    chat_events_table_name: str = "chat_events"
    connections_table_name: str = "connections"

    # Idempotency table for agent worker
    agent_idempotency_table_name: str = Field(
        default="chat_agent_idempotency",
        validation_alias="AGENT_IDEMPOTENCY_TABLE_NAME",
    )

    # Idempotency table for delivery worker
    delivery_idempotency_table_name: str = Field(
        default="chat_delivery_idempotency",
        validation_alias="DELIVERY_IDEMPOTENCY_TABLE_NAME",
    )

    # Powertools configuration
    debug: Optional[bool] = False

    # API Gateway WebSocket endpoint (for delivery worker)
    websocket_api_endpoint: Optional[str] = None


settings = Settings()
