import json
import os
import time
import uuid
from importlib import reload
from unittest.mock import MagicMock, patch

import boto3
import pytest
from moto import mock_aws

REGION = os.environ.get("AWS_REGION", "us-east-1")
ENDPOINT_URL = os.environ.get("AWS_ENDPOINT_URL")


def _create_events_table(dynamodb):
    table_name = f"chat_events_test_{uuid.uuid4().hex}"
    dynamodb.create_table(
        TableName=table_name,
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
    return table_name


@mock_aws
def test_agent_worker_processing():
    """Test the agent_worker.handler with DynamoDB Stream event"""

    dynamodb = boto3.client("dynamodb", endpoint_url=ENDPOINT_URL, region_name=REGION)
    table_name = _create_events_table(dynamodb)
    conversation_id = f"conversation#{uuid.uuid4()}"
    user_ts = int(time.time())

    dynamodb.put_item(
        TableName=table_name,
        Item={
            "channel_id": {"S": conversation_id},
            "ts": {"N": str(user_ts)},
            "created_at": {"N": str(user_ts)},
            "item_type": {"S": "message"},
            "role": {"S": "user"},
            "content": {"S": "Hello"},
        },
    )

    stream_event = {
        "Records": [
            {
                "eventID": "1",
                "eventName": "INSERT",
                "eventSource": "aws:dynamodb",
                "dynamodb": {
                    "NewImage": {
                        "channel_id": {"S": conversation_id},
                        "ts": {"N": str(user_ts)},
                        "created_at": {"N": str(user_ts)},
                        "item_type": {"S": "message"},
                        "role": {"S": "user"},
                        "content": {"S": "Hello"},
                    }
                },
            }
        ]
    }

    with patch.dict(
        os.environ,
        {"DYNAMODB_TABLE_NAME": table_name, "AWS_REGION": REGION},
    ):
        import src.rest_api.workers.agent_worker as agent_worker

        reload(agent_worker)
        response = agent_worker.handler(stream_event, {})

    items = dynamodb.scan(TableName=table_name)["Items"]
    roles = [item.get("role", {}).get("S") for item in items]

    assert response["statusCode"] == 200
    assert "assistant" in roles


@mock_aws
def test_delivery_worker_processing():
    """Test delivery_worker.handler with DynamoDB Stream event"""

    dynamodb = boto3.client("dynamodb", endpoint_url=ENDPOINT_URL, region_name=REGION)
    connections_table = f"connections_test_{uuid.uuid4().hex}"

    dynamodb.create_table(
        TableName=connections_table,
        KeySchema=[{"AttributeName": "connectionId", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "connectionId", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST",
    )
    dynamodb.put_item(
        TableName=connections_table,
        Item={"connectionId": {"S": "connection-123"}},
    )

    created_at = int(time.time())
    stream_event = {
        "Records": [
            {
                "eventID": "2",
                "eventName": "INSERT",
                "eventSource": "aws:dynamodb",
                "dynamodb": {
                    "NewImage": {
                        "channel_id": {"S": "conversation#123"},
                        "ts": {"N": str(created_at)},
                        "created_at": {"N": str(created_at)},
                        "item_type": {"S": "message"},
                        "role": {"S": "assistant"},
                        "content": {"S": "AI Response"},
                        "created_at_iso": {
                            "S": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(created_at))
                        },
                    }
                },
            }
        ]
    }

    with patch.dict(
        os.environ,
        {
            "AWS_REGION": REGION,
            "CONNECTIONS_TABLE_NAME": connections_table,
        },
    ):
        import src.rest_api.workers.delivery_worker as delivery_worker

        reload(delivery_worker)
        delivery_worker.api_gateway = MagicMock()
        response = delivery_worker.handler(stream_event, {})

        delivery_worker.api_gateway.post_to_connection.assert_called_once()
        payload = json.loads(
            delivery_worker.api_gateway.post_to_connection.call_args[1]["Data"].decode("utf-8")
        )

    assert response["statusCode"] == 200
    assert payload["content"] == "AI Response"
