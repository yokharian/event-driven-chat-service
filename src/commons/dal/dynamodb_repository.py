import dataclasses
import enum
import uuid
from collections.abc import Callable
from typing import Any

import boto3
from aws_lambda_powertools import Logger
from boto3.dynamodb.conditions import Attr, Key
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
    table_hash_key: str = "id"
    table_sort_key: str | None = None
    table_idempotency_key: str | None = None

    @property
    def table_primary_key(self) -> str:
        return self.table_hash_key

    resource: ServiceResource = dataclasses.field(init=False)
    key_auto_assign: bool = True
    key_factory: Callable = lambda: str(uuid.uuid4())

    def __post_init__(self):
        self.resource = boto3.resource("dynamodb")
        self.table = self.resource.Table(self.table_name)

    def _assign_key(self, item: dict):
        """Auto-assign primary key if key_auto_assign is enabled."""
        item[self.table_hash_key] = self.key_factory()

    def create(self, item: dict[str, Any]) -> dict[str, Any]:
        """
        Create a new item in DynamoDB.

        Auto-assigns the primary key if key_auto_assign is enabled and
        the key is not already present in the item.
        """
        # auto assign "table_hash_key" value using "key_auto_assign" in case it's enabled
        if self.key_auto_assign and item.get(self.table_hash_key) is None:
            self._assign_key(item)

        self.try_except(func=self.table.put_item, Item=item)
        return item

    def _get_item_by_full_key(self, keys: dict[str, Any]) -> dict[str, Any] | None:
        """Fetch a single item via get_item using the full primary key."""
        key_dict = {self.table_hash_key: keys[self.table_hash_key]}

        if self.table_sort_key and self.table_sort_key in keys:
            key_dict[self.table_sort_key] = keys[self.table_sort_key]

        result = self.try_except(func=self.table.get_item, Key=key_dict)
        return result.get("Item") if result else None

    def _query_by_partition(
        self,
        keys: dict[str, Any],
        filter_attributes: dict[str, Any] | None,
        limit: int | None = 1,
    ) -> list[dict[str, Any]] | None:
        """Query a partition (optionally with sort key and filters) and return first match."""
        partition_value = keys.get(self.table_hash_key)
        if partition_value is None:
            raise ValueError(
                f"Missing partition key '{self.table_hash_key}' for get_by_key"
            )

        key_condition = Key(self.table_hash_key).eq(partition_value)
        if self.table_sort_key and self.table_sort_key in keys:
            key_condition = key_condition & Key(self.table_sort_key).eq(
                keys[self.table_sort_key]
            )

        filter_expression = None
        if filter_attributes:
            for name, value in filter_attributes.items():
                expr = Attr(name).eq(value)
                filter_expression = (
                    expr if filter_expression is None else filter_expression & expr
                )

        response = self.try_except(
            func=self.table.query,
            KeyConditionExpression=key_condition,
            FilterExpression=filter_expression,
            Limit=limit,
        )
        items = response.get("Items", [])
        return items if items else None

    def get_by_key(
        self,
        *,
        raise_not_found: bool = True,
        filter_attributes: dict[str, Any] | None = None,
        limit: int | None = 1,
        **keys,
    ) -> dict[str, Any] | None:
        """
        Flexible get that supports:
        - direct get_item when full key is provided
        - partition-only query (optionally filtered) when sort key is omitted
        """
        if not self.table_hash_key:
            raise ValueError("table_hash_key must be configured")

        has_hash = self.table_hash_key in keys
        has_sort = self.table_sort_key and self.table_sort_key in keys
        provides_full_key = has_hash and (not self.table_sort_key or has_sort)

        if provides_full_key:
            item = self._get_item_by_full_key(keys)
        else:
            item = self._query_by_partition(keys, filter_attributes, limit)
            item = item[0] if item else None

        if item:
            return item
        if raise_not_found:
            raise ObjectNotFoundError(f"Object {keys} was not found")
        return None

    def get_list(self) -> list[dict[str, Any]]:
        """Get all items from the DynamoDB table using scan operation."""
        response = self.try_except(func=self.table.scan)
        return response.get("Items", [])

    def update(self, params: dict[str, Any], **keys) -> None:
        """
        Update an existing item in DynamoDB.

        Automatically handles enum serialization and prevents updating primary keys.
        """
        update_clauses = []
        expression_attribute_values = {}
        expression_attribute_names = {}

        for name, value in params.items():
            if name == self.table_hash_key or (
                self.table_sort_key and name == self.table_sort_key
            ):
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

    def search_in_secondary_index(
        self, *, index_name: str, field, value
    ) -> list[dict] | None:
        """Query DynamoDB using a secondary index (not part of interface)."""
        response = self.table.query(
            IndexName=index_name, KeyConditionExpression=Key(field).eq(value)
        )

        items = response.get("Items", [])
        if len(items) > 0:
            return items[0]
        return None

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
