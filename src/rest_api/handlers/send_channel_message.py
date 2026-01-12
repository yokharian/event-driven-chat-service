"""Lambda handler for sending channel messages."""

from typing import Any, Dict

from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.utilities.typing import LambdaContext

from commons.cors import cors_config
from rest_api.schemas import ChannelMessageCreate, ChannelMessageResponse
from rest_api.services import SendChannelMessageService
from rest_api.settings import settings

metrics = Metrics()
logger = Logger()
tracer = Tracer()

app = APIGatewayRestResolver(
    enable_validation=True,
    debug=settings.debug,
    cors=cors_config,
)


@app.post("/channels/<channel_id>/messages")
def send_channel_message(channel_id: str, data: ChannelMessageCreate) -> ChannelMessageResponse:
    """Send a message to a channel."""
    service = SendChannelMessageService()
    data.channel_id = channel_id
    result = service(message_data=data)
    return result


@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """Lambda handler for sending channel messages."""
    return app.resolve(event, context)
