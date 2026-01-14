from pydantic_settings import BaseSettings

from commons.dal import DynamoDBRepository


class Settings(BaseSettings):
    # DynamoDB configuration
    chat_events_table_idempotency_key: str = "id"
    chat_events_table_name: str = "chat_events"
    chat_events_table_pk: str = "channel_id"
    chat_events_table_sk: str = "ts"

    connections_table_name: str = "connections"
    connections_table_pk: str = "connectionId"
    connections_table_idempotency_key: str = "connectionId"


settings = Settings()

# Initialize repositories
connections_repo = DynamoDBRepository(
    table_name=settings.connections_table_name,
    table_hash_key=settings.connections_table_pk,
    table_sort_key=settings.chat_events_table_sk,
    table_idempotency_key=settings.table_idempotency_key,
    key_auto_assign=True,
)

chat_events_repository = DynamoDBRepository(
    table_name=settings.chat_events_table_name,
    table_hash_key=settings.chat_events_table_pk,
    table_sort_key=settings.chat_events_table_sk,
    key_auto_assign=True,
)
