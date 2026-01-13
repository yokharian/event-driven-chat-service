import dataclasses
from typing import Optional

from commons.dal import DynamoDBRepository
from commons.dal.interface import IRepository
from commons.repositories import settings


@dataclasses.dataclass
class BaseService:
    """
    Base service class that uses dependency injection for the repository.

    By default, it creates a DynamoDBRepository, but you can inject any
    IRepository implementation (e.g., PostgreSQLRepository) for testing
    or database migration purposes.
    """

    table_primary_key: str
    table_sort_key: Optional[str] = None
    repository: Optional[IRepository] = None
    table_name: str = ""

    def __post_init__(self):
        # Use dependency injection: if repository is not provided, create default DynamoDB repository
        if self.repository is None and self.table_name:
            self.repository = DynamoDBRepository(
                table_name=self.table_name,
                table_hash_key=self.table_primary_key,
                table_sort_key=self.table_sort_key,
                dynamodb_endpoint_url=settings.dynamodb_endpoint_url,
            )

    def __call__(self, *args, **kwargs):
        raise NotImplementedError
