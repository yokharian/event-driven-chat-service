import json
import os
import sys
from pathlib import Path
from typing import Any, Dict

from aws_lambda_powertools import Logger

# Add project root to path to import commons
# In Lambda, the package root is the function directory, so we need to go up
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from commons.dal.dynamodb_repository import DynamoDBRepository
from commons.dynamodb.exceptions import RepositoryError

logger = Logger()

# Initialize repository with settings from environment
table_name = os.environ.get("TABLE_NAME")
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
    Handle WebSocket disconnection event.
    
    Args:
        event: Lambda event containing request context with connectionId
        context: Lambda context object
        
    Returns:
        Response dictionary with statusCode and body
    """
    connection_id = event["requestContext"]["connectionId"]
    
    try:
        repository.delete(connectionId=connection_id)
        logger.info(f"Connection disconnected: {connection_id}")
    except RepositoryError as err:
        logger.error(f"Failed to disconnect: {err}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Failed to disconnect"})
        }
    
    return {"statusCode": 200, "body": "Disconnected."}
