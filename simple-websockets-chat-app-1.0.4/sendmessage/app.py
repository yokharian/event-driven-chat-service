"""
Copyright 2018-2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
SPDX-License-Identifier: MIT-0

Lambda function handler for sending messages to all connected WebSocket clients.
"""

import json
import os
from typing import Any, Dict, List

import boto3
from botocore.exceptions import ClientError

# Initialize AWS clients
dynamodb = boto3.resource("dynamodb", region_name=os.environ.get("AWS_REGION"))
table_name = os.environ.get("TABLE_NAME")


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle sending messages to all connected WebSocket clients.
    
    Args:
        event: Lambda event containing request context and body with message data
        context: Lambda context object
        
    Returns:
        Response dictionary with statusCode and body
    """
    table = dynamodb.Table(table_name)
    
    # Get all connection IDs
    try:
        response = table.scan(ProjectionExpression="connectionId")
        connection_data: List[Dict[str, str]] = response.get("Items", [])
    except ClientError as e:
        return {"statusCode": 500, "body": str(e)}
    
    # Initialize API Gateway Management API client
    request_context = event["requestContext"]
    endpoint_url = f"https://{request_context['domainName']}/{request_context['stage']}"
    
    apigw_management_api = boto3.client(
        "apigatewaymanagementapi",
        endpoint_url=endpoint_url,
        region_name=os.environ.get("AWS_REGION")
    )
    
    # Parse message data from request body
    try:
        body = json.loads(event.get("body", "{}"))
        post_data = body.get("data", "")
    except json.JSONDecodeError:
        return {"statusCode": 400, "body": "Invalid JSON in request body"}
    
    # Send message to all connections
    post_calls = []
    for item in connection_data:
        connection_id = item["connectionId"]
        try:
            apigw_management_api.post_to_connection(
                ConnectionId=connection_id,
                Data=post_data
            )
        except ClientError as e:
            # Handle stale connections (410 Gone)
            if e.response.get("Error", {}).get("Code") == "GoneException":
                print(f"Found stale connection, deleting {connection_id}")
                try:
                    table.delete_item(Key={"connectionId": connection_id})
                except ClientError as delete_err:
                    print(f"Failed to delete stale connection {connection_id}: {delete_err}")
            else:
                # Re-raise other errors
                raise
    
    return {"statusCode": 200, "body": "Data sent."}
