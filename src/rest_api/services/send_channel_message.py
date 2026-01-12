from datetime import datetime, timezone
from uuid import uuid4

from aws_lambda_powertools import Logger

from commons.schemas import ChatEventMessage
from .base import BaseService
from ..schemas import ChannelMessageCreate, ChannelMessageResponse

logger = Logger()


class SendChannelMessageService(BaseService):
    """Service to send a message to a channel."""

    def __init__(self, repository=None):
        super().__init__(
            repository=repository,
            table_name="chat_events",
        )

    def __call__(self, message_data: ChannelMessageCreate) -> ChannelMessageResponse:
        """Send a message to a channel (writes to chat_events table)."""
        logger.info(f"Sending message to channel {message_data.channel_id}")

        # Generate IDs
        event_id = str(uuid4())
        message_id = str(uuid4())
        now_dt = datetime.now(timezone.utc)
        now = int(now_dt.timestamp())
        now_iso = now_dt.isoformat().replace("+00:00", "Z")

        # Create message event (matches DynamoDB event bus schema)
        chat_event = ChatEventMessage(
            channel_id=message_data.channel_id,
            ts=now,
            created_at=now,
            event_id=event_id,
            message_id=message_id,
            sender_id=message_data.sender_id or "system",
            role=message_data.role,
            content=message_data.content,
            content_type="text",
            created_at_iso=now_iso,
        )

        # Use conditional write for idempotency (if event_id exists, skip)
        try:
            created = self.repository.create(item=chat_event.model_dump())
            logger.info(f"Successfully created message event {event_id}")
        except Exception as e:
            # If it's a conditional check failure, it's a duplicate - return success
            if "ConditionalCheckFailedException" in str(e):
                logger.info(f"Duplicate event_id {event_id}, returning existing message")
                # Try to get the existing message
                existing = self.repository.get_by_key(
                    channel_id=message_data.channel_id,
                    ts=now,
                    raise_not_found=False,
                )
                if existing:
                    existing_event = ChatEventMessage.model_validate(existing)
                    return ChannelMessageResponse.model_validate(existing_event.model_dump())
            raise

        created_event = ChatEventMessage.model_validate(created)
        return ChannelMessageResponse.model_validate(created_event.model_dump())
