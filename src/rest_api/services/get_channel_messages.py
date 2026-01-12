from aws_lambda_powertools import Logger

from .base import BaseService
from ..schemas import ChannelMessageResponse

logger = Logger()


class GetChannelMessagesService(BaseService):
    """Service to get messages for a channel."""

    def __init__(self, repository=None):
        super().__init__(
            repository=repository,
            table_name="chat_events",
        )

    def __call__(self, channel_id: str) -> list[ChannelMessageResponse]:
        """Get all messages for a channel."""
        logger.info(f"Getting messages for channel {channel_id}")

        # In a real implementation, you'd query by channel_id (partition key)
        # For now, we'll use get_list and filter
        all_messages = self.repository.get_list()

        # Filter by channel_id
        messages = [msg for msg in all_messages if msg.get("channel_id") == channel_id]

        # Sort by ts (timestamp)
        messages.sort(key=lambda x: x.get("ts", 0))

        logger.info(f"Found {len(messages)} messages for channel {channel_id}")

        return [ChannelMessageResponse.model_validate(msg) for msg in messages]
