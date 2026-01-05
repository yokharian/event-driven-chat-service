# Backward compatibility exports
from commons.dynamodb.exceptions import RepositoryError, ObjectNotFoundError
from commons.dynamodb.repository import TableRepository

__all__ = [
    "TableRepository",  # Deprecated, use commons.dal.DynamoDBRepository
    "RepositoryError",
    "ObjectNotFoundError",
]
