import asyncio
import json
import threading
from typing import Callable, Optional

import streamlit as st
import websockets
from pydantic import BaseModel


class WebSocketClient:
    def __init__(self, url: str, on_message: Callable[[str], None]):
        self.url = url
        self.on_message = on_message
        self.loop = asyncio.new_event_loop()
        self.thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self._stop_event = threading.Event()

    def _run_event_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._listen())

    async def _listen(self):
        while not self._stop_event.is_set():
            try:
                async with websockets.connect(self.url) as websocket:
                    self.ws = websocket
                    while not self._stop_event.is_set():
                        message = await websocket.recv()
                        self.on_message(message)
            except (websockets.ConnectionClosed, Exception) as e:
                print(f"WebSocket connection error: {e}")
                if not self._stop_event.is_set():
                    await asyncio.sleep(2)  # Retry after 2 seconds

    def start(self):
        self.thread.start()

    def stop(self):
        self._stop_event.set()
        
        if self.loop.is_running():
            async def close_ws():
                if self.ws:
                    try:
                        await self.ws.close()
                    except Exception:
                        pass
                # Cancel all running tasks in the loop to ensure clean exit
                for task in asyncio.all_tasks(self.loop):
                    task.cancel()

            asyncio.run_coroutine_threadsafe(close_ws(), self.loop)
        
        # Wait for thread to finish
        if self.thread.is_alive():
            self.thread.join(timeout=2.0)
