import json
import os
from typing import Any, Dict, List

import boto3
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.parser import event_parser
from aws_lambda_powertools.utilities.parser.models import APIGatewayWebSocketMessageEventModel
from botocore.exceptions import ClientError

from commons.dynamodb.exceptions import RepositoryError
from commons.repositories import connections_repo

logger = Logger()


@event_parser(model=APIGatewayWebSocketMessageEventModel)
def handler(event: APIGatewayWebSocketMessageEventModel, context: Any) -> Dict[str, Any]:
    """
    Handle sending messages to all connected WebSocket clients.

    Args:
        event: Lambda event containing request context and body with message data
        context: Lambda context object

    Returns:
        Response dictionary with statusCode and body
    """
    apigw_management_api = boto3.client("apigatewaymanagementapi")

    # Get all connection IDs using repository
    try:
        connections: List[Dict[str, Any]] = connections_repo.get_list()
        connection_ids = [conn["connectionId"] for conn in connections]
        logger.info(f"Found {len(connection_ids)} active connections")
    except RepositoryError as err:
        logger.error(f"Failed to retrieve connections: {err}", exc_info=True)
        return {"statusCode": 500, "body": json.dumps({"error": "Failed to retrieve connections"})}

    # Parse message data from request body
    try:
        body = json.loads(event.body or "{}")
        post_data = body.get("data", "")
    except json.JSONDecodeError:
        return {"statusCode": 400, "body": json.dumps({"error": "Invalid JSON in request body"})}

    # Send message to all connections
    failed_connections = []
    for connection_id in connection_ids:
        try:
            apigw_management_api.post_to_connection(ConnectionId=connection_id, Data=post_data)
        except ClientError as e:
            # Handle stale connections (410 Gone)
            error_code = e.response.get("Error", {}).get("Code")
            if error_code == "GoneException":
                logger.warning(f"Found stale connection, deleting {connection_id}")
                try:
                    connections_repo.delete(connectionId=connection_id)
                except RepositoryError as delete_err:
                    logger.error(
                        f"Failed to delete stale connection {connection_id}: {delete_err}",
                        exc_info=True,
                    )
            else:
                logger.error(
                    f"Failed to send message to connection {connection_id}: {e}", exc_info=True
                )
                failed_connections.append(connection_id)

    if failed_connections:
        logger.warning(f"Failed to send to {len(failed_connections)} connections")

    return {"statusCode": 200, "body": "Data sent."}
