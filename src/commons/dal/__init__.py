from commons.dal.dynamodb_repository import DynamoDBRepository
from commons.dal.interface import IRepository
from commons.dal.postgresql_repository import PostgreSQLRepository

__all__ = [
    "IRepository",
    "DynamoDBRepository",
    "PostgreSQLRepository",
]
