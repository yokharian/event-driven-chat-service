import logging
import os

import boto3
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


def _resolve_api_base() -> str | None:
    """Resolve the REST API base URL Fetching SSM"""
    # noinspection HttpUrlsUsage
    URL_FORMAT = "http://{FQDN}:4566/_aws/execute-api/{ID}/{STAGE}/"

    # Request api gateway id from an SSM parameter
    ssm = boto3.client(
        "ssm",
        region_name=settings.aws_default_region,
        endpoint_url=settings.aws_endpoint_url,
    )
    param = ssm.get_parameter(Name=settings.api_id_ssm_param)
    value = param.get("Parameter", {}).get("Value")
    rest_api_id = value.strip()
    logger.info(f"API ID resolved using env var api_id_ssm_param={rest_api_id}")
    return URL_FORMAT.format(
        FQDN=settings.localstack_dns, ID=rest_api_id, STAGE=settings.apigw_stage
    )


API_BASE_URL = _resolve_api_base().rstrip("/")
WS_CONN = (
    settings.docker_ws_server_url if settings.is_dockerized else settings.ws_server_url
)
