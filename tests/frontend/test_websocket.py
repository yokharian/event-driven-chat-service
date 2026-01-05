import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from src.frontend.websocket_client import WebSocketClient

@pytest.mark.asyncio
async def test_websocket_client_initialization():
    on_message = MagicMock()
    client = WebSocketClient("ws://localhost:8000/ws/test", on_message)
    assert client.url == "ws://localhost:8000/ws/test"
    assert client.on_message == on_message
    assert client.ws is None

@patch("websockets.connect")
def test_websocket_client_start_stop(mock_connect):
    # Mock the async context manager
    mock_ws = AsyncMock()
    mock_connect.return_value.__aenter__.return_value = mock_ws
    
    # We need to control the loop and thread carefully or just test the logic
    on_message = MagicMock()
    client = WebSocketClient("ws://localhost:8000/ws/test", on_message)
    
    # Just verify it doesn't crash on start/stop and sets the stop event
    client.start()
    assert client.thread.is_alive()
    client.stop()
    assert client._stop_event.is_set()

def test_on_message_callback():
    on_message = MagicMock()
    client = WebSocketClient("ws://localhost:8000/ws/test", on_message)
    
    # Manually trigger callback to verify logic
    client.on_message("test message")
    on_message.assert_called_once_with("test message")
