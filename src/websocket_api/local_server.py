"""
Local WebSocket server that mimics AWS API Gateway WebSocket API behavior.

This server allows local development without requiring API Gateway (a paid LocalStack feature).
It creates the same event structures that API Gateway would create and invokes the Lambda
handlers directly.

Usage:
    python -m src.websocket_api.local_server

Environment Variables:
    TABLE_NAME: DynamoDB table name for connections (default: connections)
    DYNAMODB_ENDPOINT_URL: LocalStack endpoint (default: http://localhost:4566)
    AWS_REGION: AWS region (default: us-east-1)
    WS_PORT: WebSocket server port (default: 8080)
"""

import asyncio
import json
import os
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from moto import mock_aws

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from websocket_api.onconnect.app import handler as onconnect_handler  # noqa: E402
from websocket_api.ondisconnect.app import handler as ondisconnect_handler  # noqa: E402
from websocket_api.sendmessage.app import handler as sendmessage_handler  # noqa: E402
from aws_lambda_powertools.utilities.parser.models import (  # noqa: E402
    APIGatewayWebSocketConnectEventModel,
    APIGatewayWebSocketConnectEventRequestContext,
    APIGatewayWebSocketDisconnectEventModel,
    APIGatewayWebSocketDisconnectEventRequestContext,
    APIGatewayWebSocketEventIdentity,
    APIGatewayWebSocketMessageEventModel,
    APIGatewayWebSocketMessageEventRequestContext,
)


class ConnectionManager:
    """Manages WebSocket connections and message delivery."""

    def __init__(self):
        self.connections: Dict[str, WebSocket] = {}

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


def create_moto_post_to_connection_hook(original_method):
    """Wrap moto's post_to_connection to also send to real WebSockets."""

    def hooked_post_to_connection(self, connection_id: str, data: bytes):
        result = original_method(self, connection_id, data)

        data_str = data.decode() if isinstance(data, bytes) else data
        if not connections.exists(connection_id):
            from botocore.exceptions import ClientError

            raise ClientError(
                {
                    "Error": {
                        "Code": "GoneException",
                        "Message": f"Connection {connection_id} gone",
                    }
                },
                "PostToConnection",
            )

        try:
            asyncio.create_task(connections.send(connection_id, data_str))
        except RuntimeError:
            asyncio.run(connections.send(connection_id, data_str))

        return result

    return hooked_post_to_connection


def _create_identity() -> APIGatewayWebSocketEventIdentity:
    """Create a minimal identity object."""
    return APIGatewayWebSocketEventIdentity.model_construct(source_ip="127.0.0.1", user_agent=None)


def _create_base_context_kwargs(connection_id: str, domain_name: str, stage: str) -> dict:
    """Create common request context kwargs."""
    now = datetime.now(timezone.utc)
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
) -> Dict[str, Any]:
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
) -> Dict[str, Any]:
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
) -> Dict[str, Any]:
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager that sets up moto mocking and backend hook."""
    from moto.apigatewaymanagementapi.models import ApiGatewayManagementApiBackend

    original_post = ApiGatewayManagementApiBackend.post_to_connection
    mock = mock_aws()
    mock.start()
    ApiGatewayManagementApiBackend.post_to_connection = create_moto_post_to_connection_hook(
        original_post
    )

    print("✓ Moto AWS mocking active")
    print("✓ API Gateway Management API hooked to local WebSockets")

    try:
        yield
    finally:
        ApiGatewayManagementApiBackend.post_to_connection = original_post
        mock.stop()
        print("✓ Moto AWS mocking stopped")


app = FastAPI(title="Local WebSocket API Gateway", lifespan=lifespan)


@app.get("/")
async def get_root():
    """Root endpoint with WebSocket test page."""
    html = """
    <!DOCTYPE html>
    <html>
    <head><title>Local WebSocket API Gateway</title></head>
    <body>
        <h1>Local WebSocket API Gateway</h1>
        <p>WebSocket endpoint: <code>ws://localhost:8080/ws</code></p>
        <div>
            <h2>Test Client</h2>
            <button onclick="connect()">Connect</button>
            <button onclick="disconnect()">Disconnect</button>
            <button onclick="sendMessage()">Send Message</button>
            <br><br>
            <input type="text" id="messageInput" placeholder="Enter message" style="width: 300px;">
            <br><br>
            <div id="messages" style="border: 1px solid #ccc; padding: 10px; height: 300px; overflow-y: auto;"></div>
        </div>
        <script>
            let ws = null;
            function connect() {
                ws = new WebSocket(`${location.protocol === 'https:' ? 'wss://' : 'ws://'}${location.host}/ws`);
                ws.onopen = () => addMessage('Connected!');
                ws.onmessage = (e) => addMessage('Received: ' + e.data);
                ws.onclose = () => addMessage('Disconnected');
                ws.onerror = (e) => addMessage('Error: ' + e);
            }
            function disconnect() { if (ws) { ws.close(); ws = null; } }
            function sendMessage() {
                const input = document.getElementById('messageInput');
                if (ws && input.value) {
                    ws.send(JSON.stringify({action: 'sendmessage', data: input.value}));
                    addMessage('Sent: ' + input.value);
                    input.value = '';
                }
            }
            function addMessage(msg) {
                const div = document.getElementById('messages');
                div.innerHTML += '<p>' + msg + '</p>';
                div.scrollTop = div.scrollHeight;
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)


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
        except Exception as exc:  # noqa: BLE001
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

    os.environ.setdefault("TABLE_NAME", "connections")
    os.environ.setdefault("DYNAMODB_ENDPOINT_URL", "http://localhost:4566")
    os.environ.setdefault("AWS_REGION", "us-east-1")

    context = LambdaContext()

    try:
        response = onconnect_handler(create_connect_event(connection_id), context)
        if response.get("statusCode") != 200:
            print(f"Connect handler failed: {response}")
            await websocket.close(code=1008, reason="Connection rejected")
            return
    except Exception as exc:  # noqa: BLE001
        print(f"Error in connect handler: {exc}")
        await websocket.close(code=1011, reason="Internal error")
        return

    try:
        while True:
            data = await websocket.receive_text()
            await handle_message(connection_id, data, context)
    except WebSocketDisconnect:
        print(f"Client disconnected: {connection_id}")
    except Exception as exc:  # noqa: BLE001
        print(f"WebSocket error: {exc}")
    finally:
        connections.remove(connection_id)
        try:
            ondisconnect_handler(create_disconnect_event(connection_id), context)
        except Exception as exc:  # noqa: BLE001
            print(f"Error in disconnect handler: {exc}")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("WS_PORT", "8080"))
    print(f"Starting local WebSocket API Gateway on ws://localhost:{port}/ws")
    print(f"Test page: http://localhost:{port}/")

    uvicorn.run(app, host="0.0.0.0", port=port)
