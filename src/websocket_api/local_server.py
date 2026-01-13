"""
Local WebSocket server that mimics AWS API Gateway WebSocket API behavior.

This server allows local development without requiring API Gateway (which is a paid
feature in LocalStack). It creates the same event structures that API Gateway would
create and invokes the Lambda handlers directly.

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
import time
import uuid
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock

import boto3
from botocore.exceptions import ClientError
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import Lambda handlers
from websocket_api.onconnect.app import handler as onconnect_handler
from websocket_api.ondisconnect.app import handler as ondisconnect_handler
from websocket_api.sendmessage.app import handler as sendmessage_handler


class ConnectionManager:
    """Manages WebSocket connections and provides API Gateway Management API emulation."""

    def __init__(self):
        self.connections: Dict[str, WebSocket] = {}

    def add_connection(self, connection_id: str, websocket: WebSocket):
        """Add a connection to the manager."""
        self.connections[connection_id] = websocket

    def remove_connection(self, connection_id: str):
        """Remove a connection from the manager."""
        if connection_id in self.connections:
            del self.connections[connection_id]

    async def send_to_connection(self, connection_id: str, data: str):
        """Send data to a connection (async)."""
        if connection_id in self.connections:
            websocket = self.connections[connection_id]
            await websocket.send_text(data)
            return True
        return False

    def __contains__(self, connection_id: str) -> bool:
        """Check if connection exists."""
        return connection_id in self.connections


# Global connection manager for API Gateway Management API emulation
_connection_manager: ConnectionManager | None = None


def set_connection_manager(manager: ConnectionManager):
    """Set the global connection manager for API Gateway Management API emulation."""
    global _connection_manager
    _connection_manager = manager


# Monkey-patch boto3 client for API Gateway Management API
# This allows the sendmessage handler to work with our local WebSocket server
_original_client = boto3.client


def patched_client(service_name, **kwargs):
    """Patch boto3.client to intercept API Gateway Management API calls."""
    if service_name == "apigatewaymanagementapi":
        # Create a mock client that uses our local connection manager
        mock_client = MagicMock()

        def post_to_connection(ConnectionId: str, Data: bytes | str):
            """Synchronous wrapper for post_to_connection."""
            data_str = Data.decode() if isinstance(Data, bytes) else Data

            if _connection_manager is None:
                raise ClientError(
                    {
                        "Error": {
                            "Code": "InternalServerError",
                            "Message": "Connection manager not initialized",
                        }
                    },
                    "PostToConnection",
                )

            # Check if connection exists
            if ConnectionId not in _connection_manager:
                raise ClientError(
                    {
                        "Error": {
                            "Code": "GoneException",
                            "Message": f"Connection {ConnectionId} not found",
                        }
                    },
                    "PostToConnection",
                )

            # Send message synchronously using asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Schedule the coroutine
                    asyncio.create_task(
                        _connection_manager.send_to_connection(ConnectionId, data_str)
                    )
                else:
                    loop.run_until_complete(
                        _connection_manager.send_to_connection(ConnectionId, data_str)
                    )
            except RuntimeError:
                # No event loop, create new one
                asyncio.run(_connection_manager.send_to_connection(ConnectionId, data_str))

            return {"ResponseMetadata": {"HTTPStatusCode": 200}}

        mock_client.post_to_connection = post_to_connection
        return mock_client

    return _original_client(service_name, **kwargs)


# Apply the patch
boto3.client = patched_client

# Initialize connection manager
connection_manager = ConnectionManager()
set_connection_manager(connection_manager)

app = FastAPI(title="Local WebSocket API Gateway")


def create_api_gateway_event(
        connection_id: str,
        route: str,
        body: str = "",
        domain_name: str = "localhost",
        stage: str = "local",
) -> Dict[str, Any]:
    """
    Create an API Gateway WebSocket event structure compatible with Powertools event models.

    The event_parser decorator in handlers will automatically parse this dictionary
    into the appropriate Powertools event model (APIGatewayWebSocketConnectEvent,
    APIGatewayWebSocketDisconnectEvent, or APIGatewayWebSocketMessageEvent).

    Args:
        connection_id: WebSocket connection ID
        route: Route key ($connect, $disconnect, sendmessage)
        body: Request body (for sendmessage)
        domain_name: API Gateway domain name
        stage: API Gateway stage

    Returns:
        Event dictionary matching API Gateway WebSocket event format
    """
    now_ms = int(time.time() * 1000)
    event_type = (
        "CONNECT" if route == "$connect" else "DISCONNECT" if route == "$disconnect" else "MESSAGE"
    )
    return {
        "headers": {},
        "multiValueHeaders": {},
        "requestContext": {
            "connectionId": connection_id,
            "domainName": domain_name,
            "stage": stage,
            "apiId": "local-api-gateway",
            "requestId": str(uuid.uuid4()),
            "extendedRequestId": str(uuid.uuid4()),
            "identity": {
                "sourceIp": "127.0.0.1",
            },
            "connectedAt": now_ms,
            "requestTime": "01/Jan/2025:00:00:00 +0000",
            "requestTimeEpoch": now_ms,
            "routeKey": route,
            "eventType": event_type,
            "messageDirection": "IN",
            "messageId": str(uuid.uuid4()),
            "disconnectStatusCode": 1000,
            "disconnectReason": "Normal Closure",
        },
        "body": body,
        "isBase64Encoded": False,
    }


def create_lambda_context() -> Any:
    """Create a minimal Lambda context object."""

    class LambdaContext:
        function_name = "local-websocket-handler"
        function_version = "$LATEST"
        invoked_function_arn = (
            "arn:aws:lambda:us-east-1:123456789012:function:local-websocket-handler"
        )
        memory_limit_in_mb = 128
        aws_request_id = str(uuid.uuid4())

    return LambdaContext()


@app.get("/")
async def get_root():
    """Root endpoint with WebSocket test page."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Local WebSocket API Gateway</title>
    </head>
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
                const wsUrl = `${location.protocol === 'https:' ? 'wss://' : 'ws://'}${location.host}/ws`;
                ws = new WebSocket(wsUrl);
                ws.onopen = () => {
                    addMessage('Connected!');
                };
                ws.onmessage = (event) => {
                    addMessage('Received: ' + event.data);
                };
                ws.onclose = () => {
                    addMessage('Disconnected');
                };
                ws.onerror = (error) => {
                    addMessage('Error: ' + error);
                };
            }
            function disconnect() {
                if (ws) {
                    ws.close();
                    ws = null;
                }
            }
            function sendMessage() {
                const input = document.getElementById('messageInput');
                if (ws && input.value) {
                    const message = JSON.stringify({
                        action: 'sendmessage',
                        data: input.value
                    });
                    ws.send(message);
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


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main WebSocket endpoint that mimics API Gateway WebSocket API."""
    await websocket.accept()

    # Generate connection ID
    connection_id = str(uuid.uuid4())
    connection_manager.add_connection(connection_id, websocket)

    print(f"New connection: {connection_id}")

    # Set environment variables for Lambda handlers
    os.environ["TABLE_NAME"] = os.getenv("TABLE_NAME", "connections")
    os.environ["DYNAMODB_ENDPOINT_URL"] = os.getenv(
        "DYNAMODB_ENDPOINT_URL", "http://localhost:4566"
    )
    os.environ["AWS_REGION"] = os.getenv("AWS_REGION", "us-east-1")

    # Create $connect event and invoke handler
    connect_event = create_api_gateway_event(connection_id, "$connect")
    context = create_lambda_context()

    try:
        response = onconnect_handler(connect_event, context)
        if response.get("statusCode") != 200:
            print(f"Connect handler failed: {response}")
            await websocket.close(code=1008, reason="Connection rejected")
            return
    except Exception as e:
        print(f"Error in connect handler: {e}")
        await websocket.close(code=1011, reason="Internal error")
        return

    # Message handling loop
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()

            try:
                # Parse message (expecting {"action": "sendmessage", "data": "..."})
                message = json.loads(data)
                action = message.get("action", "sendmessage")
                message_data = message.get("data", "")

                if action == "sendmessage":
                    # Create sendmessage event
                    send_event = create_api_gateway_event(
                        connection_id,
                        "sendmessage",
                        body=json.dumps({"data": message_data}),
                    )

                    # Invoke sendmessage handler
                    try:
                        response = sendmessage_handler(send_event, context)
                        if response.get("statusCode") != 200:
                            print(f"SendMessage handler failed: {response}")
                    except Exception as e:
                        print(f"Error in sendmessage handler: {e}")
                else:
                    print(f"Unknown action: {action}")

            except json.JSONDecodeError:
                # If not JSON, treat as plain text message
                send_event = create_api_gateway_event(
                    connection_id,
                    "sendmessage",
                    body=json.dumps({"data": data}),
                )
                try:
                    response = sendmessage_handler(send_event, context)
                except Exception as e:
                    print(f"Error in sendmessage handler: {e}")

    except WebSocketDisconnect:
        print(f"Client disconnected: {connection_id}")
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        # Clean up connection
        connection_manager.remove_connection(connection_id)

        # Create $disconnect event and invoke handler
        disconnect_event = create_api_gateway_event(connection_id, "$disconnect")
        try:
            ondisconnect_handler(disconnect_event, context)
        except Exception as e:
            print(f"Error in disconnect handler: {e}")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("WS_PORT", "8080"))
    print(f"Starting local WebSocket API Gateway on ws://localhost:{port}/ws")
    print(f"Test page: http://localhost:{port}/")

    uvicorn.run(app, host="0.0.0.0", port=port)
