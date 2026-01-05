"""
Copyright 2018-2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0

Lambda function handler for WebSocket connection events.
"""

import json
import os
from typing import Any, Dict

import boto3
from botocore.exceptions import ClientError

# Initialize DynamoDB client
dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION"))
table_name = os.environ.get("TABLE_NAME")


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle WebSocket connection event.
    
    Args:
        event: Lambda event containing request context with connectionId
        context: Lambda context object
        
    Returns:
        Response dictionary with statusCode and body
    """
    table = dynamodb.Table(table_name)
    connection_id = event["requestContext"]["connectionId"]
    
    try:
        table.put_item(
            Item={
                "connectionId": connection_id
            }
        )
    except ClientError as err:
        return {
            "statusCode": 500,
            "body": f"Failed to connect: {json.dumps(str(err))}"
        }
    
    return {"statusCode": 200, "body": "Connected."}
