import dataclasses
from typing import Optional

from commons.dal import DynamoDBRepository
from commons.dal.interface import IRepository
from ..settings import settings


@dataclasses.dataclass
class BaseService:
    """
    Base service class that uses dependency injection for the repository.

    By default, it creates a DynamoDBRepository, but you can inject any
    IRepository implementation (e.g., PostgreSQLRepository) for testing
    or database migration purposes.
    """

    repository: Optional[IRepository] = None
    table_name: str = ""

    def __post_init__(self):
        # Use dependency injection: if repository is not provided, create default DynamoDB repository
        if self.repository is None and self.table_name:
            self.repository = DynamoDBRepository(
                table_name=self.table_name,
                dynamodb_endpoint_url=settings.dynamodb_endpoint_url,
            )

    def __call__(self, *args, **kwargs):
        raise NotImplementedError
