from aws_lambda_powertools import Logger
from aws_lambda_powertools.shared.dynamodb_deserializer import TypeDeserializer

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

    def __call__(
            self, channel_id: str, message_data: ChannelMessageCreate
    ) -> ChannelMessageResponse:
        """Send a message to a channel (writes to chat_events table)."""
        logger.info(f"Sending message to channel {channel_id}")

        # Create message event (matches DynamoDB event bus schema)
        chat_event = ChatEventMessage(
            id=message_data.id,
            channel_id=channel_id,
            sender_id=message_data.sender_id or "unknown",
            role=message_data.role,
            content=message_data.content,
            content_type="text",
        )

        # Use conditional write for idempotency (if event_id exists, skip)
        # TODO convert to a transaction to comply with ACID
        exists_response = self.repository.get_by_key(raise_not_found=False, id={
            'S': chat_event.id,
        })
        if exists_response is None:
            created = self.repository.create(item=chat_event.model_dump())
            created_event = ChatEventMessage.model_validate(created)
            return ChannelMessageResponse.model_validate(created_event.model_dump())
        else:
            exists_response: dict = exists_response['Item']
            chat_event = {k: TypeDeserializer().deserialize(v) for k, v in exists_response.items()}
            chat_event = ChannelMessageResponse.model_validate(chat_event)
            return chat_event
