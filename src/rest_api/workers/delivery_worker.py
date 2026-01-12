"""Delivery Worker: AWS Lambda handler for delivering messages to WebSocket clients."""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

import boto3

from aws_lambda_powertools import Logger
from botocore.exceptions import ClientError

# Add project root to path to import commons
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from commons.dal.dynamodb_repository import DynamoDBRepository
from commons.schemas import MessageDynamoModel

logger = Logger()

# Initialize clients
api_gateway = boto3.client(
    "apigatewaymanagementapi",
    endpoint_url=os.environ.get("API_GATEWAY_ENDPOINT_URL") or None,
    region_name=os.environ.get("AWS_REGION", "us-east-1"),
)

# Initialize connections repository
connections_table_name = os.environ.get("CONNECTIONS_TABLE_NAME")
dynamodb_endpoint_url = os.environ.get("DYNAMODB_ENDPOINT_URL") or None
connections_repo = DynamoDBRepository(
    table_name=connections_table_name,
    table_hash_keys=["connectionId"],
    dynamodb_endpoint_url=dynamodb_endpoint_url,
    key_auto_assign=False,
)


def dynamodb_to_dict(item: Dict[str, Any]) -> Dict[str, Any]:
    """Convert DynamoDB format to Python dict."""
    result = {}
    for key, value in item.items():
        if "S" in value:
            result[key] = value["S"]
        elif "N" in value:
            result[key] = int(value["N"])
        elif "M" in value:
            result[key] = dynamodb_to_dict(value["M"])
    return result


def get_connections_for_channel(channel_id: str) -> list[str]:
    """Get all WebSocket connection IDs (simplified - in production, store channel->connections mapping)."""
    # For now, get all connections. In production, maintain a channel->connections mapping
    try:
        connections = connections_repo.get_list()
        return [conn.get("connectionId") for conn in connections if conn.get("connectionId")]
    except Exception as e:
        logger.error(f"Error getting connections: {e}", exc_info=True)
        return []


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

        # Convert DynamoDB format to dict
        event_data = dynamodb_to_dict(new_image)

        # Validate and parse message
        try:
            message = MessageDynamoModel(**event_data)
        except Exception as e:
            logger.error(f"Failed to parse message: {e}", exc_info=True)
            return

        logger.info(f"Delivering message to channel {message.channel_id}")

        # Get all connections for this channel
        connection_ids = get_connections_for_channel(message.channel_id)

        if not connection_ids:
            logger.info(f"No active connections for channel {message.channel_id}")
            return

        # Prepare message payload
        message_payload = {
            "id": event_data.get("message_id", ""),
            "conversation_id": message.channel_id,
            "role": message.role,
            "content": message.content,
            "timestamp": event_data.get("created_at_iso", ""),
        }

        # Broadcast to all connections
        failed_connections = []
        for connection_id in connection_ids:
            try:
                api_gateway.post_to_connection(
                    ConnectionId=connection_id,
                    Data=json.dumps(message_payload).encode("utf-8"),
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


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """AWS Lambda handler for DynamoDB Stream events."""
    logger.info(f"Received DynamoDB stream event with {len(event.get('Records', []))} records")

    for record in event.get("Records", []):
        try:
            deliver_message(record)
        except Exception as e:
            logger.error(f"Failed to deliver record: {e}", exc_info=True)
            # Re-raise to trigger Lambda retry
            raise

    return {"statusCode": 200}
