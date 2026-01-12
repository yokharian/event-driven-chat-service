import json
import sys
from pathlib import Path
from typing import Any, Dict

from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.parser import event_parser
from aws_lambda_powertools.utilities.parser.models import APIGatewayWebSocketDisconnectEventModel

# Add project root to path to import commons
# In Lambda, the package root is the function directory, so we need to go up
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from commons.dal.dynamodb_repository import DynamoDBRepository
from commons.dynamodb.exceptions import RepositoryError
from websocket_api.settings import settings

logger = Logger()

# Initialize repository with settings from environment
repository = DynamoDBRepository(
    table_name=settings.table_name,
    table_hash_keys=["connectionId"],
    dynamodb_endpoint_url=settings.dynamodb_endpoint_url,
    key_auto_assign=False,  # connectionId comes from API Gateway
)


@event_parser(model=APIGatewayWebSocketDisconnectEventModel)
def handler(event: APIGatewayWebSocketDisconnectEventModel, context: Any) -> Dict[str, Any]:
    """
    Handle WebSocket disconnection event.

    Args:
        event: Lambda event containing request context with connectionId
        context: Lambda context object

    Returns:
        Response dictionary with statusCode and body
    """
    connection_id = event.request_context.connection_id

    try:
        repository.delete(connectionId=connection_id)
        logger.info(f"Connection disconnected: {connection_id}")
    except RepositoryError as err:
        logger.error(f"Failed to disconnect: {err}", exc_info=True)
        return {"statusCode": 500, "body": json.dumps({"error": "Failed to disconnect"})}

    return {"statusCode": 200, "body": "Disconnected."}
