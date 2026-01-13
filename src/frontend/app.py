import asyncio
import json
import logging
import os
import uuid
from functools import lru_cache
from typing import Any

import aiohttp
import boto3
import requests
import streamlit as st
from pydantic import Field
from pydantic_settings import BaseSettings


def _setup_logging() -> logging.Logger:
    """Configure a simple logger for the frontend app."""
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=level,
            format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        )
    _logger = logging.getLogger("frontend.app")
    _logger.setLevel(level)
    return _logger


logger = _setup_logging()


class ConsumerSettings(BaseSettings):
    """WebSocket client configuration."""

    model_config = {"populate_by_name": True}
    aws_default_region: str = Field(default="us-east-1", alias="AWS_DEFAULT_REGION")
    aws_endpoint_url: str | None = Field(default=None, alias="AWS_ENDPOINT_URL")

    ws_base_url: str | None = Field(default=None, alias="WS_BASE_URL")

    api_id_ssm_param: str | None = Field(default=None, alias="API_ID_SSM_PARAM")
    apigw_rest_api_id: str | None = Field(default=None, alias="APIGW_REST_API_ID")
    apigw_stage: str = Field(default="local", alias="APIGW_STAGE")
    localstack_dns: str = Field(default="localstack", alias="LOCALSTACK_DNS")

    ws_server_url: str = Field(
        default="ws://0.0.0.0:8080/ws",
        alias="WS_SERVER_URL",
        description="Base WebSocket endpoint (local_server default).",
    )
    docker_ws_server_url: str = Field(
        default="",
        alias="DOCKER_WS_SERVER_URL",
        description="Docker target for the WebSocket server.",
    )
    is_dockerized: bool = Field(
        default=False,
        alias="IS_DOCKERIZED",
        description="Whether the app is running in Docker.",
    )


settings = ConsumerSettings()
WS_CONN = settings.docker_ws_server_url if settings.is_dockerized else settings.ws_server_url


@lru_cache()
def _resolve_api_base() -> str | None:
    """
    Resolve the REST API base URL. Priority:
    1) Explicit env override: APIGW_REST_API_ID
    2) Fetch SSM using env: API_ID_SSM_PARAM
    """
    URL_FORMAT = "http://{FQDN}:4566/restapis/{ID}/{STAGE}/_user_request_/"

    rest_api_id = settings.apigw_rest_api_id
    if rest_api_id:
        logger.info(f"API ID found using env var {settings.apigw_rest_api_id=}")
        return URL_FORMAT.format(
            FQDN=settings.localstack_dns, ID=rest_api_id, STAGE=settings.apigw_stage
        )

    # Request api gateway id from an SSM parameter
    ssm = boto3.client(
        "ssm", region_name=settings.aws_default_region, endpoint_url=settings.aws_endpoint_url
    )
    param = ssm.get_parameter(Name=settings.api_id_ssm_param)
    value = param.get("Parameter", {}).get("Value")
    rest_api_id = value.strip()
    logger.info(f"API ID resolved using env var api_id_ssm_param={rest_api_id}")
    return URL_FORMAT.format(
        FQDN=settings.localstack_dns, ID=rest_api_id, STAGE=settings.apigw_stage
    )


API_BASE_URL = _resolve_api_base().rstrip("/")


def _init_state() -> None:
    """Initialize session state defaults."""
    logger.debug(f"[-]{API_BASE_URL=},\n\t{WS_CONN=}")

    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("connected", False)
    st.session_state.setdefault("channel_id", "default-room")
    st.session_state.setdefault("connect_requested", False)


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
        "channel": payload.get("channel") or payload.get("channel_id") or "default-room",
        "role": payload.get("role") or "assistant",
    }


def _render_messages(container: st.delta_generator.DeltaGenerator) -> None:
    """Render chat history into the given placeholder."""
    container.empty()
    with container.container():
        for message in st.session_state.messages:
            with st.chat_message(message.get("role", "assistant")):
                st.markdown(f"**{message.get('sender', 'user')}**: {message.get('content', '')}")


def _append_message(message: dict[str, Any]) -> None:
    st.session_state.messages.append(message)


async def _chat_consumer(
        status_placeholder: st.delta_generator.DeltaGenerator,
        messages_placeholder: st.delta_generator.DeltaGenerator,
) -> None:
    """Receive messages (and optionally send one) over WebSocket, updating Streamlit placeholders in-place."""
    async with aiohttp.ClientSession(trust_env=True) as session:
        status_placeholder.subheader(f"Connecting to {WS_CONN}")
        try:
            async with session.ws_connect(WS_CONN, heartbeat=20.0) as websocket:
                status_placeholder.subheader(f"Connected to: {WS_CONN}")
                st.session_state.connected = True

                async for msg in websocket:
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
        except Exception as exc:  # noqa: BLE001
            status_placeholder.write(f"WebSocket error: {exc}")
            logger.exception(exc)
            status_placeholder.subheader("Disconnected.")
            st.session_state.connected = False
            st.session_state.connect_requested = False
            raise exc


st.set_page_config(page_title="Local WS Chat", page_icon="💬", layout="wide")
_init_state()

st.title("💬 Local WebSocket Chat")
st.caption(f"Connects to the local WebSocket API Gateway emulator at {WS_CONN}")

status = st.empty()
messages_placeholder = st.empty()

with st.sidebar:
    st.header("Connection")
    display_name = st.text_input("Display name", value="user")
    channel = st.text_input("Channel", value="default-room")
    connect_clicked = st.button("Connect to WS Server", type="primary")
    disconnect_clicked = st.button("Disconnect", type="secondary")

    if connect_clicked:
        st.session_state.connect_requested = True
        st.session_state.channel_id = channel

    if disconnect_clicked:
        st.session_state.connect_requested = False
        st.session_state.connected = False
        st.session_state.channel_id = None
        st.session_state.messages = []
        status.subheader("Disconnected.")

_render_messages(messages_placeholder)

if prompt := st.chat_input("Type a message..."):
    payload = {
        "id": str(uuid.uuid4()),
        "channel": channel,
        "sender": display_name or "user",
        "role": "user",
        "content": prompt,
    }

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
    resp = requests.get(f"{API_BASE_URL}/channels/{st.session_state.channel_id}/messages")
    st.session_state.messages = [
        {"role": m["role"], "content": m["content"], "id": m["id"]} for m in resp.json()
    ]

    asyncio.run(_chat_consumer(status, messages_placeholder))
else:
    if not st.session_state.connected:
        st.session_state.channel_id = None
        st.session_state.messages = []
        status.subheader("Disconnected.")
