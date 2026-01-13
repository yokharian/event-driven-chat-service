import json
from typing import Any, Dict

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.parser import event_parser
from aws_lambda_powertools.utilities.parser.models import APIGatewayWebSocketConnectEventModel

from commons.dynamodb.exceptions import RepositoryError
from commons.repositories import connections_repo

logger = Logger()


@event_parser(model=APIGatewayWebSocketConnectEventModel)
def handler(event: APIGatewayWebSocketConnectEventModel, context: Any) -> Dict[str, Any]:
    """
    Handle WebSocket connection event.

    Args:
        event: Lambda event containing request context with connectionId
        context: Lambda context object

    Returns:
        Response dictionary with statusCode and body
    """
    connection_id = event.request_context.connection_id

    try:
        connections_repo.create(item={"connectionId": connection_id})
        logger.info(f"Connection established: {connection_id}")
    except RepositoryError as err:
        logger.error(f"Failed to connect: {err}", exc_info=True)
        return {"statusCode": 500, "body": json.dumps({"error": "Failed to connect"})}

    return {"statusCode": 200, "body": "Connected."}
