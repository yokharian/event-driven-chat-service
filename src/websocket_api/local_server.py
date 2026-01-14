"""
Local WebSocket server that mimics AWS API Gateway WebSocket API behavior.

This server allows local development without requiring API Gateway (a paid LocalStack feature).
It creates the same event structures that API Gateway would create and invokes the Lambda
handlers directly.
"""

import asyncio
import json
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from aws_lambda_powertools.utilities.parser.models import (
    APIGatewayWebSocketConnectEventModel,
    APIGatewayWebSocketConnectEventRequestContext,
    APIGatewayWebSocketDisconnectEventModel,
    APIGatewayWebSocketDisconnectEventRequestContext,
    APIGatewayWebSocketEventIdentity,
    APIGatewayWebSocketMessageEventModel,
    APIGatewayWebSocketMessageEventRequestContext,
)
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse


# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from websocket_api.onconnect.app import handler as onconnect_handler  # noqa: E402
from websocket_api.ondisconnect.app import handler as ondisconnect_handler  # noqa: E402
from websocket_api.sendmessage.app import handler as sendmessage_handler  # noqa: E402


class ConnectionManager:
    """Manages WebSocket connections and message delivery."""

    def __init__(self):
        self.connections: dict[str, WebSocket] = {}

    def add(self, connection_id: str, websocket: WebSocket) -> None:
        """Register a new WebSocket connection."""
        self.connections[connection_id] = websocket

    def remove(self, connection_id: str) -> None:
        """Unregister a WebSocket connection."""
        self.connections.pop(connection_id, None)

    def exists(self, connection_id: str) -> bool:
        """Check if a connection is active."""
        return connection_id in self.connections

    async def send(self, connection_id: str, data: str) -> bool:
        """Send data to a specific connection. Returns True if successful."""
        if websocket := self.connections.get(connection_id):
            await websocket.send_text(data)
            return True
        return False


# Global connection manager instance
connections = ConnectionManager()


def _create_identity() -> APIGatewayWebSocketEventIdentity:
    """Create a minimal identity object."""
    return APIGatewayWebSocketEventIdentity.model_construct(source_ip="127.0.0.1", user_agent=None)


def _create_base_context_kwargs(connection_id: str, domain_name: str, stage: str) -> dict:
    """Create common request context kwargs."""
    now = datetime.now(UTC)
    return {
        "connection_id": connection_id,
        "domain_name": domain_name,
        "stage": stage,
        "api_id": "local-api-gateway",
        "request_id": str(uuid.uuid4()),
        "extended_request_id": str(uuid.uuid4()),
        "identity": _create_identity(),
        "connected_at": now,
        "request_time": "01/Jan/2025:00:00:00 +0000",
        "request_time_epoch": now,
        "message_direction": "IN",
    }


def create_connect_event(
    connection_id: str,
    domain_name: str = "localhost",
    stage: str = "local",
) -> dict[str, Any]:
    """Create a $connect event using Powertools models."""
    ctx_kwargs = _create_base_context_kwargs(connection_id, domain_name, stage)
    ctx_kwargs.update(route_key="$connect", event_type="CONNECT", message_direction="IN")

    request_context = APIGatewayWebSocketConnectEventRequestContext.model_construct(**ctx_kwargs)

    event = APIGatewayWebSocketConnectEventModel.model_construct(
        headers={},
        multi_value_headers={},
        request_context=request_context,
        is_base64_encoded=False,
    )
    return event.model_dump(by_alias=True)


def create_disconnect_event(
    connection_id: str,
    domain_name: str = "localhost",
    stage: str = "local",
) -> dict[str, Any]:
    """Create a $disconnect event using Powertools models."""
    ctx_kwargs = _create_base_context_kwargs(connection_id, domain_name, stage)
    ctx_kwargs.update(
        route_key="$disconnect",
        event_type="DISCONNECT",
        disconnect_status_code=1000,
        disconnect_reason="Normal Closure",
    )

    request_context = APIGatewayWebSocketDisconnectEventRequestContext.model_construct(**ctx_kwargs)

    event = APIGatewayWebSocketDisconnectEventModel.model_construct(
        headers={},
        multi_value_headers={},
        request_context=request_context,
        is_base64_encoded=False,
    )
    return event.model_dump(by_alias=True)


def create_message_event(
    connection_id: str,
    body: str = "",
    domain_name: str = "localhost",
    stage: str = "local",
) -> dict[str, Any]:
    """Create a sendmessage event using Powertools models."""
    ctx_kwargs = _create_base_context_kwargs(connection_id, domain_name, stage)
    ctx_kwargs.update(
        route_key="sendmessage",
        event_type="MESSAGE",
        message_direction="IN",
        message_id=str(uuid.uuid4()),
    )

    request_context = APIGatewayWebSocketMessageEventRequestContext.model_construct(**ctx_kwargs)

    event = APIGatewayWebSocketMessageEventModel.model_construct(
        request_context=request_context,
        is_base64_encoded=False,
        body=body,
    )
    return event.model_dump(by_alias=True)


class LambdaContext:
    """Minimal Lambda context for local invocation."""

    function_name = "local-websocket-handler"
    function_version = "$LATEST"
    invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:local-websocket-handler"
    memory_limit_in_mb = 128

    def __init__(self):
        self.aws_request_id = str(uuid.uuid4())


def _create_local_apigw_client(connection_manager: ConnectionManager):
    """
    Create a mock API Gateway Management API client that sends to local WebSockets.

    This is necessary because:
    1. LocalStack's apigatewaymanagementapi is a paid feature
    2. moto's mock_aws() doesn't intercept calls with explicit endpoint_url
    3. sendmessage/app.py passes endpoint_url to boto3.client()
    """
    from unittest.mock import MagicMock

    from botocore.exceptions import ClientError

    mock_client = MagicMock()

    def post_to_connection(ConnectionId: str, Data: bytes | str):
        data_str = Data.decode() if isinstance(Data, bytes) else Data

        if not connection_manager.exists(ConnectionId):
            raise ClientError(
                {"Error": {"Code": "GoneException", "Message": f"Connection {ConnectionId} gone"}},
                "PostToConnection",
            )

        try:
            asyncio.create_task(connection_manager.send(ConnectionId, data_str))
        except RuntimeError:
            asyncio.run(connection_manager.send(ConnectionId, data_str))

        return {"ResponseMetadata": {"HTTPStatusCode": 200}}

    mock_client.post_to_connection = post_to_connection
    return mock_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager that patches boto3 for local WebSocket delivery.

    We patch boto3.client directly (not using moto) because:
    - sendmessage/app.py uses explicit endpoint_url which bypasses moto
    - LocalStack doesn't support apigatewaymanagementapi in free tier
    """
    import boto3

    original_client = boto3.client

    def patched_client(service_name, *args, **kwargs):
        if service_name == "apigatewaymanagementapi":
            return _create_local_apigw_client(connections)
        return original_client(service_name, *args, **kwargs)

    boto3.client = patched_client

    from websocket_api.onconnect.app import handler as onconnect_handler  # noqa: E402
    from websocket_api.ondisconnect.app import handler as ondisconnect_handler  # noqa: E402
    from websocket_api.sendmessage.app import handler as sendmessage_handler  # noqa: E402

    print("✓ API Gateway Management API patched for local WebSocket delivery")

    try:
        yield
    finally:
        boto3.client = original_client
        print("✓ boto3.client restored")


app = FastAPI(title="Local WebSocket API Gateway", lifespan=lifespan)


@app.get("/")
async def get_root():
    """Serve the WebSocket test page from index.html."""
    return FileResponse(Path(__file__).parent / "index.html")


async def handle_message(connection_id: str, data: str, context: LambdaContext) -> None:
    """Process an incoming WebSocket message."""
    try:
        message = json.loads(data)
        action = message.get("action", "sendmessage")
        message_data = message.get("data", "")
    except json.JSONDecodeError:
        action = "sendmessage"
        message_data = data

    if action == "sendmessage":
        event = create_message_event(
            connection_id,
            body=json.dumps({"data": message_data}),
        )
        try:
            response = sendmessage_handler(event, context)
            if response.get("statusCode") != 200:
                print(f"SendMessage handler failed: {response}")
        except Exception as exc:
            print(f"Error in sendmessage handler: {exc}")
    else:
        print(f"Unknown action: {action}")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint that mimics API Gateway WebSocket API."""
    await websocket.accept()

    connection_id = str(uuid.uuid4())
    connections.add(connection_id, websocket)
    print(f"New connection: {connection_id}")

    context = LambdaContext()

    try:
        response = onconnect_handler(create_connect_event(connection_id), context)
        if response.get("statusCode") != 200:
            print(f"Connect handler failed: {response}")
            await websocket.close(code=1008, reason="Connection rejected")
            return
    except Exception as exc:
        print(f"Error in connect handler: {exc}")
        await websocket.close(code=1011, reason="Internal error")
        return

    try:
        while True:
            data = await websocket.receive_text()
            await handle_message(connection_id, data, context)
    except WebSocketDisconnect:
        print(f"Client disconnected: {connection_id}")
    except Exception as exc:
        print(f"WebSocket error: {exc}")
    finally:
        connections.remove(connection_id)
        try:
            ondisconnect_handler(create_disconnect_event(connection_id), context)
        except Exception as exc:
            print(f"Error in disconnect handler: {exc}")
