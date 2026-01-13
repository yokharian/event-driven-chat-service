from aws_lambda_powertools import Logger

from commons.schemas import ChatEventMessage
from .base import BaseService
from ..schemas import ChannelMessageCreate, ChannelMessageResponse

logger = Logger()


class SendChannelMessageService(BaseService):

    def __call__(
        self, channel_id: str, message_data: ChannelMessageCreate
    ) -> ChannelMessageResponse:
        """Send a message to a channel (idempotent write)."""
        logger.info(f"Processing message {message_data.id} for channel {channel_id}")

        repo_pk = self.repository.table_primary_key

        # Create a message event (matches DynamoDB event bus schema)
        chat_event = ChatEventMessage(
            id=message_data.id,
            channel_id=channel_id,
            sender_id=message_data.sender_id or "unknown",
            role=message_data.role,
            content=message_data.content,
            content_type="text",
        )
        event_partition_value = chat_event.model_dump().get(repo_pk)

        # search existing
        found = self.repository.get_by_key(
            **{repo_pk: event_partition_value},  # channel
            filter_attributes={"id": message_data.id},
            raise_not_found=False,
            limit=1,
        )
        if found:
            logger.info(f"Duplicate message {chat_event.id}, returning existing")
            return ChannelMessageResponse.model_validate(found)

        created = self.repository.create(item=chat_event.model_dump())
        logger.info(f"Created message {chat_event.id}")
        return ChannelMessageResponse.model_validate(created)
