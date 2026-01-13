import asyncio
import json
from contextlib import suppress
from typing import Any
from uuid import uuid4

import aiohttp
import requests
import streamlit as st

from commons.schemas import ChatEventMessage

from .config import API_BASE_URL, WS_CONN, logger


def _init_state() -> None:
    """Initialize session state defaults."""
    logger.debug(f"[-]{ API_BASE_URL=},\n\t{ WS_CONN=}")

    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("connected", False)
    st.session_state.setdefault("channel_id", "default-room")
    st.session_state.setdefault("connect_requested", False)
    st.session_state.setdefault("disconnect_requested", False)
    st.session_state.setdefault("ws_client", None)


def _extract_message(payload: Any) -> dict[str, Any]:
    """Normalize inbound payloads into a chat message dict."""
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            return {
                "content": payload,
                "sender": "server",
                "channel": "default-room",
                "role": "assistant",
            }

    if not isinstance(payload, dict):
        return {
            "content": str(payload),
            "sender": "server",
            "channel": "default-room",
            "role": "assistant",
        }

    return {
        "content": payload.get("content") or payload.get("data") or "",
        "sender": payload.get("sender") or payload.get("role") or "server",
        "channel": payload.get("channel")
        or payload.get("channel_id")
        or "default-room",
        "role": payload.get("role") or "assistant",
    }


def _render_messages(container: st.delta_generator.DeltaGenerator) -> None:
    """Render chat history into the given placeholder."""
    container.empty()
    with container.container():
        for message in st.session_state.messages:
            with st.chat_message(message.get("role", "assistant")):
                st.markdown(
                    f"**{message.get('sender', 'user')}**: {message.get('content', '')}"
                )


def _append_message(message: dict[str, Any]) -> None:
    st.session_state.messages.append(message)


async def _chat_consumer(
    status_placeholder: st.delta_generator.DeltaGenerator,
    messages_placeholder: st.delta_generator.DeltaGenerator,
) -> None:
    """Receive messages (and optionally send one) over WebSocket, updating Streamlit placeholders in-place."""
    st.session_state.disconnect_requested = False
    async with aiohttp.ClientSession(trust_env=True) as session:
        status_placeholder.subheader(f"Connecting to {WS_CONN}")
        try:
            async with session.ws_connect(WS_CONN, heartbeat=20.0) as websocket:
                st.session_state.ws_client = websocket
                status_placeholder.subheader(f"Connected to: {WS_CONN}")
                st.session_state.connected = True

                async for msg in websocket:
                    if st.session_state.get("disconnect_requested"):
                        await websocket.close()
                        break
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        payload_raw = msg.data
                        try:
                            payload = json.loads(payload_raw)
                        except (TypeError, ValueError) as exc:
                            payload = payload_raw
                            logger.info(f"Received message: {payload}")
                            logger.exception(exc)

                        parsed = _extract_message(payload)
                        _append_message(parsed)
                        _render_messages(messages_placeholder)
                    elif msg.type == aiohttp.WSMsgType.BINARY:
                        try:
                            decoded = msg.data.decode("utf-8")
                            payload = json.loads(decoded)
                        except (UnicodeDecodeError, TypeError, ValueError) as exc:
                            logger.info(f"Received message: {payload}")
                            logger.exception(exc)
                            payload = {
                                "content": "<binary>",
                                "sender": "server",
                                "channel": "default-room",
                                "role": "assistant",
                            }

                        parsed = _extract_message(payload)
                        _append_message(parsed)
                        _render_messages(messages_placeholder)
                    elif msg.type in (
                        aiohttp.WSMsgType.CLOSE,
                        aiohttp.WSMsgType.CLOSED,
                        aiohttp.WSMsgType.ERROR,
                    ):
                        break
        except Exception as exc:
            status_placeholder.write(f"WebSocket error: {exc}")
            logger.exception(exc)
            raise exc
        finally:
            with suppress(Exception):
                if st.session_state.get("ws_client") is not None:
                    await st.session_state.ws_client.close()
            st.session_state.ws_client = None
            status_placeholder.subheader("Disconnected.")
            st.session_state.connected = False
            st.session_state.connect_requested = False
            st.session_state.disconnect_requested = False


st.set_page_config(page_title="Local WS Chat", page_icon="💬", layout="wide")
_init_state()

st.title("💬 Local WebSocket Chat")
st.caption(f"Connects to the local WebSocket API Gateway emulator at {WS_CONN}")

status = st.empty()
messages_placeholder = st.empty()

with st.sidebar:
    st.header("Connection")
    display_name = st.text_input("Display name", value=str(uuid4()).split("-")[0])
    channel = st.text_input("Channel", value="default-room")
    connect_clicked = st.button("Connect to WS Server", type="primary")
    disconnect_clicked = st.button("Disconnect", type="secondary")

    if connect_clicked:
        st.session_state.connect_requested = True
        st.session_state.disconnect_requested = False
        st.session_state.channel_id = channel

    if disconnect_clicked:
        st.session_state.connect_requested = False
        st.session_state.disconnect_requested = True
        st.session_state.connected = False
        st.session_state.channel_id = None
        st.session_state.messages = []
        ws_client = st.session_state.get("ws_client")
        if ws_client is not None:
            with suppress(Exception):
                asyncio.run(ws_client.close())
        st.session_state.ws_client = None
        status.subheader("Disconnected.")


if prompt := st.chat_input("Type a message..."):
    message = ChatEventMessage(
        channel_id=channel,
        sender_id=display_name,
        role="user",
        content=prompt,
        content_type="txt",
    )
    payload = message.model_dump()
    _append_message(payload)
    _render_messages(messages_placeholder)
    resp = requests.post(
        f"{API_BASE_URL}/channels/{st.session_state.channel_id}/messages", json=payload
    )
    if resp.status_code != 200:
        st.error(f"Failed to send message: {resp.text}")
    else:
        status.write("message sent")

if st.session_state.get("connect_requested"):
    st.session_state.channel_id = channel
    resp = requests.get(
        f"{API_BASE_URL}/channels/{st.session_state.channel_id}/messages"
    )
    resp.raise_for_status()
    st.session_state.messages = [
        {"role": message["role"], "content": message["content"], "id": message["id"]}
        for message in resp.json()
    ]
    asyncio.run(_chat_consumer(status, messages_placeholder))
elif not st.session_state.connected:
    st.session_state.channel_id = None
    st.session_state.messages = []
    status.subheader("Disconnected.")
