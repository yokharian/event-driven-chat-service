"""
Tests for WebSocket API Lambda handlers using Moto for AWS service mocking.

These tests use Moto decorators to mock AWS services (DynamoDB, API Gateway Management API)
without requiring actual AWS credentials or LocalStack.
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import boto3
import pytest
from botocore.exceptions import ClientError
from moto import mock_aws

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Set default env vars early so handler module imports can construct repositories
os.environ.setdefault("TABLE_NAME", "test_connections")
os.environ.setdefault("AWS_REGION", "us-east-1")
os.environ.setdefault("DYNAMODB_ENDPOINT_URL", "http://localhost:4566")

from websocket_api.onconnect.app import handler as onconnect_handler
from websocket_api.ondisconnect.app import handler as ondisconnect_handler
from websocket_api.sendmessage.app import handler as sendmessage_handler


@pytest.fixture
def lambda_context():
    """Create a minimal Lambda context object."""

    class LambdaContext:
        function_name = "test-handler"
        function_version = "$LATEST"
        invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:test-handler"
        memory_limit_in_mb = 128
        aws_request_id = "test-request-id"

    return LambdaContext()


@pytest.fixture
def set_env_vars(monkeypatch):
    """Set environment variables for handlers."""
    monkeypatch.setenv("TABLE_NAME", "test_connections")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("DYNAMODB_ENDPOINT_URL", "")


def _make_request_context(
    route_key: str,
    event_type: str,
    connection_id: str = "test-connection-123",
    *,
    domain_name: str = "test.execute-api.us-east-1.amazonaws.com",
    stage: str = "test",
) -> dict:
    """Build a Powertools-compatible requestContext payload."""
    return {
        "connectionId": connection_id,
        "domainName": domain_name,
        "stage": stage,
        "apiId": "test-api-id",
        "requestId": "test-request-id",
        "extendedRequestId": "test-extended-id",
        "identity": {"sourceIp": "127.0.0.1"},
        "connectedAt": 1_234_567_890,
        "requestTime": "01/Jan/2025:00:00:00 +0000",
        "requestTimeEpoch": 1_234_567_890,
        "routeKey": route_key,
        "eventType": event_type,
        "messageDirection": "IN",
        "messageId": "test-message-id",
        "disconnectStatusCode": 1000,
        "disconnectReason": "Normal Closure",
    }


def _make_event(
    route_key: str, event_type: str, *, body: str = "", connection_id: str = None
) -> dict:
    """Assemble a full API Gateway WebSocket event."""
    return {
        "headers": {},
        "multiValueHeaders": {},
        "requestContext": _make_request_context(
            route_key=route_key,
            event_type=event_type,
            connection_id=connection_id or "test-connection-123",
        ),
        "body": body,
        "isBase64Encoded": False,
    }


class TestOnConnectHandler:
    """Tests for the onconnect handler."""

    @mock_aws
    def test_connect_success(self, set_env_vars, lambda_context):
        """Test successful WebSocket connection."""
        # Create table
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        try:
            dynamodb.create_table(
                TableName="test_connections",
                KeySchema=[{"AttributeName": "connectionId", "KeyType": "HASH"}],
                AttributeDefinitions=[{"AttributeName": "connectionId", "AttributeType": "S"}],
                BillingMode="PAY_PER_REQUEST",
            )
        except dynamodb.meta.client.exceptions.ResourceInUseException:
            pass

        # Create event
        event = _make_event(route_key="$connect", event_type="CONNECT")

        # Invoke handler
        response = onconnect_handler(event, lambda_context)

        # Verify response
        assert response["statusCode"] == 200
        assert response["body"] == "Connected."

        # Verify connection was stored in DynamoDB
        table = dynamodb.Table("test_connections")
        item = table.get_item(Key={"connectionId": "test-connection-123"})
        assert "Item" in item
        assert item["Item"]["connectionId"] == "test-connection-123"


class TestOnDisconnectHandler:
    """Tests for the ondisconnect handler."""

    @mock_aws
    def test_disconnect_success(self, set_env_vars, lambda_context):
        """Test successful WebSocket disconnection."""
        # Create table with existing connection
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        try:
            table = dynamodb.create_table(
                TableName="test_connections",
                KeySchema=[{"AttributeName": "connectionId", "KeyType": "HASH"}],
                AttributeDefinitions=[{"AttributeName": "connectionId", "AttributeType": "S"}],
                BillingMode="PAY_PER_REQUEST",
            )
        except dynamodb.meta.client.exceptions.ResourceInUseException:
            table = dynamodb.Table("test_connections")
        table.put_item(Item={"connectionId": "test-connection-123"})

        # Create event
        event = _make_event(route_key="$disconnect", event_type="DISCONNECT")

        # Invoke handler
        response = ondisconnect_handler(event, lambda_context)

        # Verify response
        assert response["statusCode"] == 200
        assert response["body"] == "Disconnected."

        # Verify connection was removed from DynamoDB
        item = table.get_item(Key={"connectionId": "test-connection-123"})
        assert "Item" not in item


class TestSendMessageHandler:
    """Tests for the sendmessage handler."""

    @mock_aws
    def test_send_message_success(self, set_env_vars, lambda_context):
        """Test successful message broadcast to all connections."""
        # Create table with multiple connections
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        try:
            table = dynamodb.create_table(
                TableName="test_connections",
                KeySchema=[{"AttributeName": "connectionId", "KeyType": "HASH"}],
                AttributeDefinitions=[{"AttributeName": "connectionId", "AttributeType": "S"}],
                BillingMode="PAY_PER_REQUEST",
            )
        except dynamodb.meta.client.exceptions.ResourceInUseException:
            table = dynamodb.Table("test_connections")
        table.put_item(Item={"connectionId": "conn-1"})
        table.put_item(Item={"connectionId": "conn-2"})
        table.put_item(Item={"connectionId": "conn-3"})

        # Create event
        event = _make_event(
            route_key="sendmessage",
            event_type="MESSAGE",
            connection_id="sender-connection",
            body=json.dumps({"data": "Hello, world!"}),
        )

        # Mock API Gateway Management API
        with patch("boto3.client") as mock_client:
            mock_apigw = MagicMock()
            mock_apigw.post_to_connection.return_value = {
                "ResponseMetadata": {"HTTPStatusCode": 200}
            }
            mock_client.return_value = mock_apigw

            # Invoke handler
            response = sendmessage_handler(event, lambda_context)

        # Verify response
        assert response["statusCode"] == 200
        assert response["body"] == "Data sent."

        # Verify post_to_connection was called for each connection
        assert mock_apigw.post_to_connection.call_count == 3

    @mock_aws
    def test_send_message_deletes_stale_connections(self, set_env_vars, lambda_context):
        """Stale connections (410 Gone) are removed from DynamoDB."""
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        try:
            table = dynamodb.create_table(
                TableName="test_connections",
                KeySchema=[{"AttributeName": "connectionId", "KeyType": "HASH"}],
                AttributeDefinitions=[{"AttributeName": "connectionId", "AttributeType": "S"}],
                BillingMode="PAY_PER_REQUEST",
            )
        except dynamodb.meta.client.exceptions.ResourceInUseException:
            table = dynamodb.Table("test_connections")
        table.put_item(Item={"connectionId": "conn-1"})
        table.put_item(Item={"connectionId": "conn-2"})

        event = _make_event(
            route_key="sendmessage",
            event_type="MESSAGE",
            connection_id="sender-connection",
            body=json.dumps({"data": "Hello, world!"}),
        )

        with patch("boto3.client") as mock_client:
            mock_apigw = MagicMock()

            def _post_to_connection(ConnectionId: str, Data: str):
                if ConnectionId == "conn-1":
                    raise ClientError({"Error": {"Code": "GoneException"}}, "PostToConnection")
                return {"ResponseMetadata": {"HTTPStatusCode": 200}}

            mock_apigw.post_to_connection.side_effect = _post_to_connection
            mock_client.return_value = mock_apigw

            response = sendmessage_handler(event, lambda_context)

        assert response["statusCode"] == 200
        assert "Item" not in table.get_item(Key={"connectionId": "conn-1"})
        assert "Item" in table.get_item(Key={"connectionId": "conn-2"})

    @mock_aws
    def test_send_message_invalid_json(self, set_env_vars, lambda_context):
        """Test handling of invalid JSON in request body."""
        # Create table
        dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        try:
            dynamodb.create_table(
                TableName="test_connections",
                KeySchema=[{"AttributeName": "connectionId", "KeyType": "HASH"}],
                AttributeDefinitions=[{"AttributeName": "connectionId", "AttributeType": "S"}],
                BillingMode="PAY_PER_REQUEST",
            )
        except dynamodb.meta.client.exceptions.ResourceInUseException:
            pass

        # Create event with invalid JSON
        event = _make_event(
            route_key="sendmessage",
            event_type="MESSAGE",
            connection_id="sender-connection",
            body="invalid json {",
        )

        # Invoke handler
        response = sendmessage_handler(event, lambda_context)

        # Verify error response
        assert response["statusCode"] == 400
        error_body = json.loads(response["body"])
        assert "error" in error_body
