"""Delivery Worker: AWS Lambda handler for delivering messages to WebSocket clients."""

from typing import Any

import httpx
from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.shared.dynamodb_deserializer import TypeDeserializer
from aws_lambda_powertools.utilities.data_classes import (
    DynamoDBStreamEvent,
    event_source,
)
from aws_lambda_powertools.utilities.idempotency import (
    DynamoDBPersistenceLayer,
    IdempotencyConfig,
    idempotent_function,
)
from aws_lambda_powertools.utilities.typing import LambdaContext

from commons.repositories import (
    Settings as CommonRepositoriesSettings,
)
from commons.schemas import ChatEventMessage


metrics = Metrics()
logger = Logger()
tracer = Tracer()


class Settings(CommonRepositoriesSettings):
    localstack_runtime_id: str | None = None  # str if running localstack
    localstack_dns: str = "localstack"
    delivery_idempotency_table_name: str
    rest_api_id: str
    rest_api_stage: str
    rest_api_region: str
    rest_api_endpoint: str = "/channels/{channel}/messages/websocket"


settings = Settings()


persistence_layer = DynamoDBPersistenceLayer(
    table_name=settings.delivery_idempotency_table_name,
    key_attr="id",
    expiry_attr="expiration",
)

idempotency_config = IdempotencyConfig(
    event_key_jmespath="dynamodb.NewImage.id.S",
    expires_after_seconds=3600,
    use_local_cache=False,
)

if settings.localstack_runtime_id:
    # noinspection HttpUrlsUsage
    API_URL = "http://{FQDN}:4566/_aws/execute-api/{ID}/{STAGE}/"
    API_URL = API_URL.format(
        FQDN=settings.localstack_dns,
        ID=settings.rest_api_id,
        STAGE=settings.rest_api_region,
    )
else:
    API_URL = "https://{ID}.execute-api.{REGION}.amazonaws.com/{STAGE}/"
    API_URL = API_URL.format(
        ID=settings.rest_api_id,
        REGION=settings.rest_api_region,
        STAGE=settings.rest_api_stage,
    )


def _build_endpoint_url(channel_id: str) -> str:
    endpoint = settings.rest_api_endpoint.format(channel=channel_id)
    return f"{API_URL.rstrip('/')}/{endpoint.lstrip('/')}"


async def _post_message(message: ChatEventMessage) -> None:
    url = _build_endpoint_url(channel_id=message.channel_id)
    payload = message.model_dump(by_alias=True)

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
        logger.info(
            "Delivered message via REST", url=url, channel_id=message.channel_id
        )
    except httpx.HTTPStatusError as exc:
        logger.error(
            "REST delivery failed",
            url=url,
            status_code=exc.response.status_code,
            response_text=exc.response.text,
            exc_info=True,
        )
        raise
    except Exception as exc:
        logger.error("REST delivery error", url=url, error=str(exc), exc_info=True)
        raise


@idempotent_function(
    data_keyword_argument="record",
    persistence_store=persistence_layer,
    config=idempotency_config,
)
async def deliver_message(record: dict[str, Any]) -> None:
    """Send a message to WebSocket clients."""
    # Only process INSERT events (new messages)
    if record.get("eventName") != "INSERT":
        logger.info(f"Skipping non-INSERT event: {record.get('eventName')}")
        return

    new_image = record.get("dynamodb", {}).get("NewImage", {})
    if not new_image:
        logger.warning("No NewImage in stream record")
        return

    # Validate and parse message
    ddb_deserializer = TypeDeserializer()
    try:
        deserialized = {
            k: ddb_deserializer.deserialize(v) for k, v in new_image.items()
        }
        message = ChatEventMessage(**deserialized)
    except Exception as e:
        logger.error(f"Failed to parse message: {e}", exc_info=True)
        return

    logger.info(f"Delivering message to channel {message.channel_id}")
    await _post_message(message=message)


@event_source(data_class=DynamoDBStreamEvent)
@logger.inject_lambda_context()
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
async def handler(event: DynamoDBStreamEvent, context: LambdaContext):
    """AWS Lambda handler for DynamoDB Stream events."""
    logger.info(
        f"Received DynamoDB stream event with {len(event.get('Records', []))} records"
    )

    for record in event.get("Records", []):
        try:
            await deliver_message(
                record=record
            )  # Must use keyword argument for idempotency
        except Exception as e:
            logger.error(f"Failed to deliver record: {e}", exc_info=True)
            # Re-raise to trigger Lambda retry
            raise

    return {"statusCode": 200}
