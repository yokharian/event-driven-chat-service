import pytest
import asyncio
import threading
import json
import websockets
from unittest.mock import MagicMock, patch
from src.frontend.websocket_client import WebSocketClient


@pytest.mark.asyncio
async def test_websocket_integration():
    # 1. Start a mock websocket server
    received_messages = []

    async def mock_server(websocket):
        await websocket.send(json.dumps({"content": "hello from server", "role": "assistant"}))
        # Keep connection open for a bit
        await asyncio.sleep(0.5)

    server = await websockets.serve(mock_server, "localhost", 8765)

    # 2. Setup client
    msg_received = asyncio.Event()

    def on_message(msg):
        received_messages.append(msg)
        msg_received.set()

    client = WebSocketClient("ws://localhost:8765", on_message)

    # 3. Start client
    client.start()

    # 4. Wait for message
    try:
        await asyncio.wait_for(msg_received.wait(), timeout=2.0)
    except asyncio.TimeoutError:
        pytest.fail("Did not receive message from mock server")
    finally:
        client.stop()
        server.close()
        await server.wait_closed()

    # 5. Assertions
    assert len(received_messages) == 1
    data = json.loads(received_messages[0])
    assert data["content"] == "hello from server"


@pytest.mark.asyncio
async def test_websocket_multiple_messages():
    """Test receiving multiple messages from WebSocket server."""
    received_messages = []

    async def mock_server(websocket):
        for i in range(3):
            await websocket.send(json.dumps({"content": f"Message {i}", "role": "assistant"}))
            await asyncio.sleep(0.1)
        await asyncio.sleep(0.5)

    server = await websockets.serve(mock_server, "localhost", 8766)

    msg_count = 0

    def on_message(msg):
        nonlocal msg_count
        received_messages.append(msg)
        msg_count += 1

    client = WebSocketClient("ws://localhost:8766", on_message)
    client.start()

    # Wait for messages
    await asyncio.sleep(1.0)

    client.stop()
    server.close()
    await server.wait_closed()

    # Should receive all 3 messages
    assert len(received_messages) == 3
    for i, msg in enumerate(received_messages):
        data = json.loads(msg)
        assert data["content"] == f"Message {i}"


@pytest.mark.asyncio
async def test_websocket_reconnection_after_disconnect():
    """Test that WebSocket client reconnects after server disconnects."""
    connection_count = [0]

    async def mock_server(websocket):
        connection_count[0] += 1
        if connection_count[0] == 1:
            # First connection: send message then close
            await websocket.send(json.dumps({"content": "First", "role": "assistant"}))
            await asyncio.sleep(0.2)
            await websocket.close()
        else:
            # Second connection: send message
            await websocket.send(json.dumps({"content": "Reconnected", "role": "assistant"}))
            await asyncio.sleep(0.5)

    server = await websockets.serve(mock_server, "localhost", 8767)

    received_messages = []

    def on_message(msg):
        received_messages.append(msg)

    client = WebSocketClient("ws://localhost:8767", on_message)
    client.start()

    # Wait for reconnection
    await asyncio.sleep(3.0)

    client.stop()
    server.close()
    await server.wait_closed()

    # Should have reconnected and received messages from both connections
    assert connection_count[0] >= 2
    # Should have received at least one message
    assert len(received_messages) >= 1


@pytest.mark.asyncio
async def test_websocket_json_message_parsing():
    """Test that JSON messages are properly parsed by the callback."""

    async def mock_server(websocket):
        # Send various message formats
        await websocket.send(json.dumps({"content": "Hello", "role": "assistant", "id": "1"}))
        await websocket.send(json.dumps({"content": "World", "role": "user"}))
        await websocket.send("Plain text message")  # Non-JSON
        await asyncio.sleep(0.5)

    server = await websockets.serve(mock_server, "localhost", 8768)

    received_messages = []

    def on_message(msg):
        received_messages.append(msg)

    client = WebSocketClient("ws://localhost:8768", on_message)
    client.start()

    await asyncio.sleep(1.0)

    client.stop()
    server.close()
    await server.wait_closed()

    # Should receive all 3 messages (JSON and plain text)
    assert len(received_messages) == 3
    # First two should be JSON strings
    assert json.loads(received_messages[0])["content"] == "Hello"
    assert json.loads(received_messages[1])["content"] == "World"
    # Third should be plain text
    assert received_messages[2] == "Plain text message"
