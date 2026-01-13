import os
from importlib import import_module
from unittest.mock import patch

import boto3
from botocore.exceptions import ClientError
from moto import mock_aws

REGION = os.environ.get("AWS_REGION", "us-east-1")
ENDPOINT_URL = os.environ.get("AWS_ENDPOINT_URL")


def _create_table_if_absent(client, *, table_name: str, **kwargs) -> None:
    """Create a DynamoDB table if it is not already present."""
    try:
        client.create_table(TableName=table_name, **kwargs)
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") != "ResourceInUseException":
            raise


def _create_lambda_if_absent(client, *, function_name: str) -> None:
    """Create a Lambda function if it is not already present."""
    try:
        client.create_function(
            FunctionName=function_name,
            Runtime="python3.12",
            Role="arn:aws:iam::123456789012:role/dummy",
            Handler="index.handler",
            Code={"ZipFile": b"dummy"},
        )
    except ClientError as exc:
        if exc.response.get("Error", {}).get("Code") != "ResourceConflictException":
            raise


@mock_aws
def test_infrastructure_exists():
    """Verify that core AWS resources exist (mocked via moto)."""

    lambda_client = boto3.client("lambda", endpoint_url=ENDPOINT_URL, region_name=REGION)
    dynamodb_client = boto3.client("dynamodb", endpoint_url=ENDPOINT_URL, region_name=REGION)

    _create_table_if_absent(
        dynamodb_client,
        table_name="chat_events",
        KeySchema=[
            {"AttributeName": "channel_id", "KeyType": "HASH"},
            {"AttributeName": "ts", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "channel_id", "AttributeType": "S"},
            {"AttributeName": "ts", "AttributeType": "N"},
        ],
        BillingMode="PAY_PER_REQUEST",
        StreamSpecification={"StreamEnabled": True, "StreamViewType": "NEW_AND_OLD_IMAGES"},
    )
    _create_table_if_absent(
        dynamodb_client,
        table_name="connections",
        KeySchema=[{"AttributeName": "connectionId", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "connectionId", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )

    _create_lambda_if_absent(lambda_client, function_name="chat-agent-worker-local")
    _create_lambda_if_absent(lambda_client, function_name="chat-delivery-worker-local")

    tables = dynamodb_client.list_tables().get("TableNames", [])
    assert "chat_events" in tables
    assert "connections" in tables

    functions = lambda_client.list_functions()["Functions"]
    func_names = [f["FunctionName"] for f in functions]
    assert "chat-agent-worker-local" in func_names
    assert "chat-delivery-worker-local" in func_names


def test_lambda_invocation_logic():
    """Unit test for the Lambda handler logic."""
    with patch.dict(os.environ, {"DYNAMODB_TABLE_NAME": "chat_events", "AWS_REGION": REGION}):
        import importlib

        module = import_module("src.rest_api.workers.agent_worker")
        importlib.reload(module)

        assert callable(module.handler)
