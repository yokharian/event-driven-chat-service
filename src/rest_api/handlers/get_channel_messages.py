"""Lambda handler for getting channel messages."""

from typing import Any, Dict, List

from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.utilities.typing import LambdaContext

from commons.cors import cors_config
from commons.repositories import chat_events_repository
from rest_api.schemas import ChannelMessageResponse
from rest_api.services import GetChannelMessagesService

metrics = Metrics()
logger = Logger()
tracer = Tracer()

app = APIGatewayRestResolver(
    enable_validation=True,
    cors=cors_config,
)


@app.get("/channels/<channel_id>/messages")
def get_channel_messages(channel_id: str) -> List[ChannelMessageResponse]:
    """Get messages from a channel."""
    service = GetChannelMessagesService(repository=chat_events_repository)
    result = service(channel_id=channel_id)
    return result


@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """Lambda handler for getting channel messages."""
    return app.resolve(event, context)
