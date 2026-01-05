import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

import boto3
from aws_lambda_powertools import Logger
from botocore.exceptions import ClientError

# Add project root to path to import commons
# In Lambda, the package root is the function directory, so we need to go up
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from commons.dal.dynamodb_repository import DynamoDBRepository
from commons.dynamodb.exceptions import RepositoryError

logger = Logger()

# Initialize repository with settings from environment
table_name = os.environ.get("TABLE_NAME")
aws_region = os.environ.get("AWS_REGION", "us-east-1")
dynamodb_endpoint_url = os.environ.get("DYNAMODB_ENDPOINT_URL")  # Optional, for LocalStack
repository = DynamoDBRepository(
    table_name=table_name,
    table_hash_keys=["connectionId"],
    dynamodb_endpoint_url=dynamodb_endpoint_url,
    key_auto_assign=False,  # connectionId comes from API Gateway
)

logger = Logger()

# Initialize repository
repository = DynamoDBRepository(
    table_name=settings.table_name,
    table_hash_keys=["connectionId"],
    dynamodb_endpoint_url=settings.dynamodb_endpoint_url,
    key_auto_assign=False,  # connectionId comes from API Gateway
)


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Handle sending messages to all connected WebSocket clients.
    
    Args:
        event: Lambda event containing request context and body with message data
        context: Lambda context object
        
    Returns:
        Response dictionary with statusCode and body
    """
    # Get all connection IDs using repository
    try:
        connections: List[Dict[str, Any]] = repository.get_list()
        connection_ids = [conn["connectionId"] for conn in connections]
        logger.info(f"Found {len(connection_ids)} active connections")
    except RepositoryError as err:
        logger.error(f"Failed to retrieve connections: {err}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Failed to retrieve connections"})
        }
    
    # Initialize API Gateway Management API client
    request_context = event["requestContext"]
    endpoint_url = f"https://{request_context['domainName']}/{request_context['stage']}"
    
    apigw_management_api = boto3.client(
        "apigatewaymanagementapi",
        endpoint_url=endpoint_url,
        region_name=aws_region
    )
    
    # Parse message data from request body
    try:
        body = json.loads(event.get("body", "{}"))
        post_data = body.get("data", "")
    except json.JSONDecodeError:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Invalid JSON in request body"})
        }
    
    # Send message to all connections
    failed_connections = []
    for connection_id in connection_ids:
        try:
            apigw_management_api.post_to_connection(
                ConnectionId=connection_id,
                Data=post_data
            )
        except ClientError as e:
            # Handle stale connections (410 Gone)
            error_code = e.response.get("Error", {}).get("Code")
            if error_code == "GoneException":
                logger.warning(f"Found stale connection, deleting {connection_id}")
                try:
                    repository.delete(connectionId=connection_id)
                except RepositoryError as delete_err:
                    logger.error(
                        f"Failed to delete stale connection {connection_id}: {delete_err}",
                        exc_info=True
                    )
            else:
                logger.error(
                    f"Failed to send message to connection {connection_id}: {e}",
                    exc_info=True
                )
                failed_connections.append(connection_id)
    
    if failed_connections:
        logger.warning(f"Failed to send to {len(failed_connections)} connections")
    
    return {"statusCode": 200, "body": "Data sent."}
