import dataclasses
import enum
import uuid
from typing import Optional, Dict, Any, List

import boto3
from aws_lambda_powertools import Logger
from boto3.dynamodb.conditions import Key
from boto3.resources.base import ServiceResource
from botocore.exceptions import ClientError

from commons.dal.interface import IRepository
from commons.dynamodb.exceptions import ObjectNotFoundError, RepositoryError

logger = Logger()


@dataclasses.dataclass
class DynamoDBRepository(IRepository):
    """
    DynamoDB implementation of the IRepository interface.

    This repository handles all DynamoDB-specific operations while adhering
    to the Data Access Layer contract defined by IRepository.
    """

    table_name: str
    table_hash_keys: list[str] = dataclasses.field(default_factory=list)
    resource: ServiceResource = dataclasses.field(init=False)
    dynamodb_endpoint_url: Optional[str] = None
    key_auto_assign: bool = True
    key_factory: callable = lambda: str(uuid.uuid4())

    def __post_init__(self):
        if not self.table_hash_keys:
            self.table_hash_keys = ["id"]
        self.resource = boto3.resource(
            "dynamodb",
            endpoint_url=self.dynamodb_endpoint_url,
        )
        self.table = self.resource.Table(self.table_name)

    def _assign_key(self, item: dict):
        """Auto-assign primary key if key_auto_assign is enabled."""
        item[self.table_hash_keys[0]] = self.key_factory()

    def create(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new item in DynamoDB.

        Auto-assigns the primary key if key_auto_assign is enabled and
        the key is not already present in the item.
        """
        # auto assign "table_hash_key" value using "key_auto_assign" in case it's enabled
        if self.key_auto_assign:
            if len(self.table_hash_keys) != 1:
                raise ValueError("Only one hash key is supported for the `key_auto_assign` feature")
            if item.get(self.table_hash_keys[0]) is None:
                self._assign_key(item)

        self.try_except(func=self.table.put_item, Item=item)
        return item

    def get_by_key(self, *, raise_not_found: bool = True, **keys) -> Optional[Dict[str, Any]]:
        """Get an item by its primary key(s)."""
        result = self.try_except(func=self.table.get_item, Key=keys)
        if result and (item := result.get("Item")):
            return item
        if raise_not_found:
            raise ObjectNotFoundError(f"Object {keys} was not found")
        return None

    def get_list(self) -> List[Dict[str, Any]]:
        """Get all items from the DynamoDB table using scan operation."""
        response = self.try_except(func=self.table.scan)
        return response.get("Items", [])

    def update(self, params: Dict[str, Any], **keys) -> None:
        """
        Update an existing item in DynamoDB.

        Automatically handles enum serialization and prevents updating primary keys.
        """
        update_clauses = []
        expression_attribute_values = {}
        expression_attribute_names = {}

        for name, value in params.items():
            if name in self.table_hash_keys:
                continue
            if isinstance(value, enum.Enum):
                value = value.value
            update_clauses.append(f"#{name} = :{name}")
            expression_attribute_values[f":{name}"] = value
            expression_attribute_names[f"#{name}"] = name
        update_expression = "SET " + ", ".join(update_clauses)

        self.try_except(
            func=self.table.update_item,
            Key=keys,
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_attribute_values,
            ExpressionAttributeNames=expression_attribute_names,
            ReturnValues="ALL_NEW",
        )

    def delete(self, **keys) -> None:
        """Delete an item from DynamoDB by its primary key(s)."""
        self.try_except(
            func=self.table.delete_item,
            Key=keys,
        )

    # DynamoDB-specific methods (not part of interface, but preserved for backward compatibility)
    def search(self, *, params: dict, limit) -> list[dict]:
        """DynamoDB-specific search method (not part of interface)."""
        raise NotImplementedError

    def search_in_secondary_index(self, *, index_name: str, field, value) -> list[dict]:
        """Query DynamoDB using a secondary index (not part of interface)."""
        response = self.table.query(
            IndexName=index_name, KeyConditionExpression=Key(field).eq(value)
        )

        items = response.get("Items", [])
        if len(items) > 0:
            return items[0]

    def try_except(self, func: callable, *args, **kwargs):
        """
        Wrapper for DynamoDB operations that handles exceptions and converts
        them to repository-specific exceptions.
        """
        try:
            return func(*args, **kwargs)
        except ClientError as err:
            msg = f"Error while calling '{func.__name__}' for '{self.table_name=}'. Reason: {err.response['Error']}"
            logger.error(msg, stack_info=True)
            raise RepositoryError(msg) from err
        except Exception as err:
            msg = f"Error while calling '{func.__name__}' for '{self.table_name=}'. Reason: {err}"
            logger.error(msg, stack_info=True)
            raise RepositoryError(msg) from err
