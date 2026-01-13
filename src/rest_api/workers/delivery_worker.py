"""Delivery Worker: AWS Lambda handler for delivering messages to WebSocket clients."""

from typing import Any, Dict

import boto3
from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.utilities.data_classes import event_source, DynamoDBStreamEvent
from aws_lambda_powertools.utilities.idempotency import (
    DynamoDBPersistenceLayer,
    IdempotencyConfig,
    idempotent_function,
)
from aws_lambda_powertools.utilities.typing import LambdaContext
from botocore.exceptions import ClientError

from commons.repositories import connections_repo
from commons.schemas import ChatEventMessage
from rest_api.settings import settings

metrics = Metrics()
logger = Logger()
tracer = Tracer()

# Initialize clients
api_gateway = boto3.client("apigatewaymanagementapi")

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


def get_connections_for_channel(channel_id: str) -> list[str]:
    """Get all WebSocket connection IDs (simplified - in production, store channel->connections mapping)."""
    # For now, get all connections. In production, maintain a channel->connections mapping
    try:
        connections = connections_repo.get_list()
        return [conn.get("connectionId") for conn in connections if conn.get("connectionId")]
    except Exception as e:
        logger.error(f"Error getting connections: {e}", exc_info=True)
        return []


@idempotent_function(
    data_keyword_argument="record",
    persistence_store=persistence_layer,
    config=idempotency_config,
)
def deliver_message(record: Dict[str, Any]) -> None:
    """Send a message to WebSocket clients."""
    try:
        # Only process INSERT events (new messages)
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

        logger.info(f"Delivering message to channel {message.channel_id}")

        # Get all connections for this channel
        connection_ids = get_connections_for_channel(message.channel_id)

        if not connection_ids:
            logger.info(f"No active connections for channel {message.channel_id}")
            return

        # Broadcast to all connections
        failed_connections = []
        for connection_id in connection_ids:
            try:
                api_gateway.post_to_connection(
                    ConnectionId=connection_id,
                    Data=message.model_dump().encode("utf-8"),
                )
                logger.debug(f"Sent message to connection {connection_id}")
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "")
                if error_code == "GoneException":
                    # Connection is stale, remove it
                    logger.info(f"Removing stale connection: {connection_id}")
                    try:
                        connections_repo.delete(connectionId=connection_id)
                    except Exception:
                        pass
                    failed_connections.append(connection_id)
                else:
                    logger.error(f"Error sending to connection {connection_id}: {e}")
                    failed_connections.append(connection_id)

        logger.info(
            f"✓ Delivered message to {len(connection_ids) - len(failed_connections)}/{len(connection_ids)} connections"
        )

    except Exception as e:
        logger.error(f"Error delivering message: {e}", exc_info=True)
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
            deliver_message(record=record)  # Must use keyword argument for idempotency
        except Exception as e:
            logger.error(f"Failed to deliver record: {e}", exc_info=True)
            # Re-raise to trigger Lambda retry
            raise

    return {"statusCode": 200}
