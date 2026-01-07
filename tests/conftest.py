import os
from typing import AsyncGenerator

import boto3
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from moto import mock_aws

try:
    from src.backend.database import _configure_models
    from src.backend.config import settings
    from src.backend.main import app

    _backend_available = True
except ImportError:
    _backend_available = False


@pytest.fixture(scope="function")
def aws_credentials():
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    os.environ["ENVIRONMENT"] = "testing"


@pytest.fixture(scope="function")
def mocked_aws(aws_credentials):
    with mock_aws():
        yield


@pytest.fixture(scope="function")
def dynamodb_table(mocked_aws):
    """Create DynamoDB table for testing."""
    if not _backend_available:
        pytest.skip("backend package not available in this environment")
    client = boto3.client("dynamodb", region_name="us-east-1")

    table_name = "chat-data-test"
    client.create_table(
        TableName=table_name,
        KeySchema=[
            {"AttributeName": "conversation_id", "KeyType": "HASH"},
            {"AttributeName": "created_at", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "conversation_id", "AttributeType": "S"},
            {"AttributeName": "created_at", "AttributeType": "N"},
            {"AttributeName": "message_id", "AttributeType": "S"},
        ],
        GlobalSecondaryIndexes=[
            {
                "IndexName": "MessageIdIndex",
                "KeySchema": [
                    {"AttributeName": "message_id", "KeyType": "HASH"},
                    {"AttributeName": "created_at", "KeyType": "RANGE"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
        BillingMode="PAY_PER_REQUEST",
    )

    # Override table name in settings
    original_table_name = settings.DYNAMODB_TABLE_NAME
    settings.DYNAMODB_TABLE_NAME = table_name

    # Reconfigure PynamoDB models with new table name
    _configure_models()

    yield table_name

    # Cleanup
    settings.DYNAMODB_TABLE_NAME = original_table_name
    _configure_models()
    client.delete_table(TableName=table_name)


@pytest_asyncio.fixture
async def client(dynamodb_table) -> AsyncGenerator[AsyncClient, None]:
    """FastAPI test client with DynamoDB table."""
    if not _backend_available:
        pytest.skip("backend package not available in this environment")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sqs_client(mocked_aws):
    return boto3.client("sqs", region_name="us-east-1")
