from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict

from commons.dal import DynamoDBRepository


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    # DynamoDB configuration
    dynamodb_endpoint_url: Optional[str] = None
    chat_events_table_name: str = "chat_events"
    connections_table_name: str = "connections"


settings = Settings()

# Initialize repositories
connections_repo = DynamoDBRepository(
    table_name=settings.connections_table_name,
    table_hash_keys=["connectionId"],
    dynamodb_endpoint_url=settings.dynamodb_endpoint_url,
    key_auto_assign=True,
)

chat_events_repository = DynamoDBRepository(
    table_name=settings.chat_events_table_name,
    table_hash_keys=["id"],
    dynamodb_endpoint_url=settings.dynamodb_endpoint_url,
    key_auto_assign=True,
)
