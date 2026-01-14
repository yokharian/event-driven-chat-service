"""Lambda handler for sending channel messages over WebSocket via REST."""

from typing import Any

from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.event_handler import APIGatewayRestResolver
from aws_lambda_powertools.logging import correlation_paths
from aws_lambda_powertools.utilities.typing import LambdaContext

from commons.cors import cors_config
from commons.repositories import connections_repo
from rest_api.schemas import ChannelMessageCreateWebsocket, ChannelMessageWebsocket
from rest_api.services.send_channel_message_websocket import (
    SendChannelMessageWebsocketService,
)


metrics = Metrics()
logger = Logger()
tracer = Tracer()

app = APIGatewayRestResolver(
    enable_validation=True,
    cors=cors_config,
)


@app.post("/channels/<channel_id>/messages/websocket")
def send_channel_message_websocket(
    channel_id: str, data: ChannelMessageCreateWebsocket
) -> ChannelMessageWebsocket:
    """Send a message to a channel via WebSocket broadcast."""
    service = SendChannelMessageWebsocketService(repository=connections_repo)
    result = service(channel_id=channel_id, message_data=data)
    return result


@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_REST)
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def handler(event: dict[str, Any], context: LambdaContext) -> dict[str, Any]:
    """Lambda handler for REST-to-WebSocket message broadcasting."""
    return app.resolve(event, context)
