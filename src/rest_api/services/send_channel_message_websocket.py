from dataclasses import dataclass, field
from typing import Any

import boto3
from aws_lambda_powertools import Logger
from botocore.exceptions import ClientError

from commons.dynamodb.exceptions import RepositoryError
from rest_api.schemas import (
    ChannelMessageCreateWebsocket,
    ChannelMessageWebsocket,
)

from .base import BaseService


logger = Logger()


@dataclass
class SendChannelMessageWebsocketService(BaseService):
    """Service to broadcast channel messages to all WebSocket connections."""

    _apigw_client: Any = field(default=None, init=False, repr=False)

    def __post_init__(self):
        if self._apigw_client is None:
            self._apigw_client = boto3.client("apigatewaymanagementapi")

    def _load_connections(self) -> list[dict]:
        try:
            return self.repository.get_list()
        except RepositoryError as err:
            logger.error(
                "Failed to retrieve connections", error=str(err), exc_info=True
            )
            raise

    def _broadcast(self, payload: str, connection_ids: list[str]) -> None:
        stale_connections: list[str] = []
        failed_connections: list[str] = []

        for connection_id in connection_ids:
            try:
                self._apigw_client.post_to_connection(
                    ConnectionId=connection_id, Data=payload
                )
            except ClientError as exc:
                error_code: str | None = exc.response.get("Error", {}).get("Code")
                if error_code == "GoneException":
                    stale_connections.append(connection_id)
                else:
                    failed_connections.append(connection_id)
                    logger.error(
                        "Failed to send message to connection",
                        connection_id=connection_id,
                        error=str(exc),
                        exc_info=True,
                    )

        for stale_id in stale_connections:
            try:
                logger.warning(
                    "Pruning stale WebSocket connection", connection_id=stale_id
                )
                self.repository.delete(connectionId=stale_id)
            except RepositoryError as err:
                logger.error(
                    "Failed to prune stale connection",
                    connection_id=stale_id,
                    error=str(err),
                    exc_info=True,
                )

        if failed_connections:
            logger.warning(
                "Some WebSocket sends failed",
                failed_connection_count=len(failed_connections),
                failed_connections=failed_connections,
            )

    def __call__(
        self,
        channel_id: str,
        message_data: ChannelMessageCreateWebsocket,
    ) -> ChannelMessageWebsocket:
        """Broadcast a channel message to all active WebSocket connections."""
        message = ChannelMessageWebsocket(
            id=getattr(message_data, "id", None),
            channel_id=channel_id,
            sender_id=message_data.sender_id,
            content=message_data.content,
            metadata=getattr(message_data, "metadata", None),
            role=message_data.role,
        )

        payload = message.model_dump_json(by_alias=True)

        connections = self._load_connections()
        connection_ids = [
            conn.get("connectionId") for conn in connections if conn.get("connectionId")
        ]

        if not connection_ids:
            logger.info("No active WebSocket connections; nothing to broadcast")
            return message

        self._broadcast(payload, connection_ids)
        return message
