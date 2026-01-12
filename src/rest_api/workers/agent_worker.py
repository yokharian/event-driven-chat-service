"""Agent Worker: AWS Lambda handler for processing user messages from DynamoDB Streams."""

import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

from aws_lambda_powertools import Logger

# Add project root to path to import commons
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from commons.dal.dynamodb_repository import DynamoDBRepository
from commons.schemas import MessageDynamoModel

logger = Logger()

# Initialize repository
table_name = os.environ.get("DYNAMODB_TABLE_NAME")
dynamodb_endpoint_url = os.environ.get("DYNAMODB_ENDPOINT_URL") or None
repository = DynamoDBRepository(
    table_name=table_name,
    table_hash_keys=["channel_id", "ts"],
    dynamodb_endpoint_url=dynamodb_endpoint_url,
    key_auto_assign=False,  # Keys come from the event
)


def generate_ai_response(user_message: str) -> str:
    """Generate a mock AI response (synchronous)."""
    # TODO: Replace with actual LLM call
    return f"AI Response to: {user_message}"


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

        # Convert DynamoDB format to dict
        # DynamoDB format: {"S": "value"} for strings, {"N": "123"} for numbers
        def dynamodb_to_dict(item: Dict[str, Any]) -> Dict[str, Any]:
            result = {}
            for key, value in item.items():
                if "S" in value:
                    result[key] = value["S"]
                elif "N" in value:
                    result[key] = int(value["N"])
                elif "M" in value:
                    result[key] = dynamodb_to_dict(value["M"])
            return result

        event_data = dynamodb_to_dict(new_image)

        # Validate and parse message
        try:
            message = MessageDynamoModel(**event_data)
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

        # Create AI message in DynamoDB
        now = int(datetime.now(timezone.utc).timestamp())
        event_id = str(uuid4())

        ai_message = {
            "channel_id": message.channel_id,
            "ts": now,
            "event_id": event_id,
            "message_id": str(uuid4()),
            "role": "assistant",
            "content": ai_content,
            "item_type": "message",
            "created_at": now,
            "created_at_iso": datetime.now(timezone.utc).isoformat(),
        }

        repository.create(item=ai_message)
        logger.info(f"✓ Generated AI response for channel {message.channel_id}")

    except Exception as e:
        logger.error(f"Error processing user message: {e}", exc_info=True)
        raise


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """AWS Lambda handler for DynamoDB Stream events."""
    logger.info(f"Received DynamoDB stream event with {len(event.get('Records', []))} records")

    for record in event.get("Records", []):
        try:
            process_user_message(record)
        except Exception as e:
            logger.error(f"Failed to process record: {e}", exc_info=True)
            # Re-raise to trigger Lambda retry
            raise

    return {"statusCode": 200}
