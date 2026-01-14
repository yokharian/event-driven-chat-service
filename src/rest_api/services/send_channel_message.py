from aws_lambda_powertools import Logger

from ..schemas import ChannelMessageCreate, ChannelMessageResponse
from .base import BaseService


logger = Logger()


class SendChannelMessageService(BaseService):

    def __call__(
        self, channel_id: str, message_data: ChannelMessageCreate
    ) -> ChannelMessageResponse:
        """Send a message to a channel (idempotent write)."""
        logger.info(f"Processing message {message_data.id} for channel {channel_id}")

        repo_pk = self.repository.table_primary_key
        repo_id = self.repository.table_idempotency_key
        message_pk = message_data.model_dump().get(repo_pk)
        message_id = message_data.model_dump().get(repo_id)

        # search existing
        found = self.repository.get_by_key(
            **{repo_pk: message_pk},  # channel
            filter_attributes={repo_id: message_id},
            raise_not_found=False,
            limit=1,
        )
        if found:
            logger.info(f"Duplicate message {message_id}, returning existing")
            return ChannelMessageResponse.model_validate(found)

        created = self.repository.create(item=message_data.model_dump())
        logger.info(f"Created message {message_id}")
        return ChannelMessageResponse.model_validate(created)
