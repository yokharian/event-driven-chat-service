"""Agent Worker: AWS Lambda handler for processing user messages from DynamoDB Streams."""

from typing import Any, Dict

from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.utilities.data_classes import event_source, DynamoDBStreamEvent
from aws_lambda_powertools.utilities.idempotency import (
    DynamoDBPersistenceLayer,
    IdempotencyConfig,
    idempotent_function,
)
from aws_lambda_powertools.utilities.typing import LambdaContext

from commons.repositories import chat_events_repository
from commons.schemas import ChatEventMessage

from commons.repositories import Settings as CommonRepositoriesSettings


class Settings(CommonRepositoriesSettings):
    agent_idempotency_table_name: str



settings = Settings()


metrics = Metrics()
logger = Logger()
tracer = Tracer()

persistence_layer = DynamoDBPersistenceLayer(
    table_name=settings.agent_idempotency_table_name,
    key_attr="id",
    expiry_attr="expiration",
)

idempotency_config = IdempotencyConfig(
    event_key_jmespath="dynamodb.NewImage.id.S",  # Extract id from DynamoDB stream record
    expires_after_seconds=3600,  # 1 hour TTL
    use_local_cache=False,  # Reduce DynamoDB reads
)


def generate_ai_response(user_message: str) -> str:
    """Generate a mock AI response (synchronous)."""
    # TODO: Replace with actual LLM call
    return f"AI Response to: {user_message}"


@idempotent_function(
    data_keyword_argument="record",
    persistence_store=persistence_layer,
    config=idempotency_config,
)
def process_user_message(record: Dict[str, Any]) -> None:
    """Process a user message from DynamoDB Stream and generate an AI response."""
    try:
        # DynamoDB Stream records have 'dynamodb' key with 'NewImage' for inserts
        if record.get("eventName") != "INSERT":
            logger.info(f"Skipping non-INSERT event: {record.get('eventName')}")
            return

        new_image = record.get("dynamodb", {}).get("NewImage", {})
        if not new_image:
            logger.warning("No NewImage in stream record")
            return

        # Validate and parse message
        try:
            message = ChatEventMessage(**new_image)
        except Exception as e:
            logger.error(f"Failed to parse message: {e}", exc_info=True)
            return

        # Only process user messages
        if message.role != "user":
            logger.info(f"Skipping non-user message with role: {message.role}")
            return

        logger.info(f"Processing user message: {message.content[:50]}...")

        # Generate AI Response
        ai_content = generate_ai_response(message.content)

        # Create message event (matches DynamoDB event bus schema)
        chat_event = ChatEventMessage(
            channel_id=message.channel_id,
            sender_id="assistant-llm",
            role="assistant",
            content=ai_content,
            content_type="text",
        )
        chat_events_repository.create(item=chat_event.model_dump())
        logger.info(f"✓ Generated AI response for channel {message.channel_id}")
    except Exception as e:
        logger.error(f"Error processing user message: {e}", exc_info=True)
        raise


@event_source(data_class=DynamoDBStreamEvent)
@logger.inject_lambda_context()
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def handler(event: DynamoDBStreamEvent, context: LambdaContext):
    """AWS Lambda handler for DynamoDB Stream events."""
    logger.info(f"Received DynamoDB stream event with {len(event.get('Records', []))} records")

    for record in event.get("Records", []):
        try:
            process_user_message(record=record)  # Must use keyword argument for idempotency
        except Exception as e:
            logger.error(f"Failed to process record: {e}", exc_info=True)
            # Re-raise to trigger Lambda retry
            raise

    return {"statusCode": 200}
