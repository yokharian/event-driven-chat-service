import dataclasses
import enum
import uuid
from typing import Optional, Dict, Any, List

import psycopg2
from aws_lambda_powertools import Logger
from psycopg2.extras import RealDictCursor

from commons.dal.interface import IRepository
from commons.dynamodb.exceptions import ObjectNotFoundError, RepositoryError

logger = Logger()


@dataclasses.dataclass
class PostgreSQLRepository(IRepository):
    """
    PostgreSQL implementation of the IRepository interface.

    This repository handles all PostgreSQL-specific operations while adhering
    to the Data Access Layer contract defined by IRepository.

    Note: This is a basic implementation. For production use, consider:
    - Connection pooling
    - Transaction management
    - Prepared statements
    - Query optimization
    """
    
    table_name: str
    connection_string: str
    primary_key: str = "id"
    key_auto_assign: bool = True
    key_factory: callable = lambda: str(uuid.uuid4())
    _connection: Optional[Any] = dataclasses.field(init=False, default=None)
    
    def __post_init__(self):
        """Initialize the PostgreSQL connection."""
        self._connection = None
    
    def _get_connection(self):
        """Get or create a database connection."""
        if self._connection is None or self._connection.closed:
            self._connection = psycopg2.connect(self.connection_string)
        return self._connection
    
    def _execute_query(
            self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute a SELECT query and return results as dictionaries."""
        conn = self._get_connection()
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params or {})
                results = cursor.fetchall()
                return [dict(row) for row in results]
        except psycopg2.Error as err:
            msg = f"Error executing query on '{self.table_name}'. Reason: {err}"
            logger.error(msg, stack_info=True)
            raise RepositoryError(msg) from err
    
    def _execute_update(
            self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> None:
        """Execute an INSERT, UPDATE, or DELETE query."""
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(query, params or {})
                conn.commit()
        except psycopg2.Error as err:
            conn.rollback()
            msg = f"Error executing update on '{self.table_name}'. Reason: {err}"
            logger.error(msg, stack_info=True)
            raise RepositoryError(msg) from err
    
    def _assign_key(self, item: Dict[str, Any]) -> None:
        """Auto-assign primary key if key_auto_assign is enabled."""
        item[self.primary_key] = self.key_factory()
    
    def _serialize_value(self, value: Any) -> Any:
        """Serialize enum values and other special types."""
        if isinstance(value, enum.Enum):
            return value.value
        return value
    
    def create(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new item in PostgreSQL.

        Auto-assigns the primary key if key_auto_assign is enabled and
        the key is not already present in the item.
        """
        # Auto-assign primary key if enabled
        if self.key_auto_assign and item.get(self.primary_key) is None:
            self._assign_key(item)
        
        # Serialize enum values
        serialized_item = {k: self._serialize_value(v) for k, v in item.items()}
        
        # Build INSERT query
        columns = ", ".join(serialized_item.keys())
        placeholders = ", ".join([f"%({col})s" for col in serialized_item.keys()])
        query = f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders}) RETURNING *"
        
        # Execute and return the created item
        result = self._execute_query(query, serialized_item)
        if result:
            return result[0]
        return serialized_item
    
    def get_by_key(
            self, *, raise_not_found: bool = True, **keys
    ) -> Optional[Dict[str, Any]]:
        """Get an item by its primary key(s)."""
        if not keys:
            raise ValueError("At least one key must be provided")
        
        # Build WHERE clause
        conditions = [f"{key} = %({key})s" for key in keys.keys()]
        where_clause = " AND ".join(conditions)
        query = f"SELECT * FROM {self.table_name} WHERE {where_clause} LIMIT 1"
        
        result = self._execute_query(query, keys)
        if result:
            return result[0]
        
        if raise_not_found:
            raise ObjectNotFoundError(f"Object {keys} was not found")
        return None
    
    def get_list(self) -> List[Dict[str, Any]]:
        """Get all items from the PostgreSQL table."""
        query = f"SELECT * FROM {self.table_name}"
        return self._execute_query(query)
    
    def update(self, params: Dict[str, Any], **keys) -> None:
        """
        Update an existing item in PostgreSQL.

        Prevents updating primary key fields.
        """
        if not keys:
            raise ValueError(
                "At least one key must be provided to identify the item to update"
            )
        
        # Filter out primary key from update params
        update_params = {
            k: self._serialize_value(v)
            for k, v in params.items()
            if k != self.primary_key
        }
        
        if not update_params:
            logger.warning("No fields to update (all fields are primary keys)")
            return
        
        # Build UPDATE query
        set_clauses = [f"{col} = %({col})s" for col in update_params.keys()]
        set_clause = ", ".join(set_clauses)
        
        key_conditions = [f"{key} = %(key_{key})s" for key in keys.keys()]
        where_clause = " AND ".join(key_conditions)
        
        # Prefix key params to avoid conflicts
        all_params = {**update_params, **{f"key_{k}": v for k, v in keys.items()}}
        
        query = f"UPDATE {self.table_name} SET {set_clause} WHERE {where_clause}"
        
        self._execute_update(query, all_params)
    
    def delete(self, **keys) -> None:
        """Delete an item from PostgreSQL by its primary key(s)."""
        if not keys:
            raise ValueError("At least one key must be provided")
        
        # Build WHERE clause
        conditions = [f"{key} = %({key})s" for key in keys.keys()]
        where_clause = " AND ".join(conditions)
        query = f"DELETE FROM {self.table_name} WHERE {where_clause}"
        
        self._execute_update(query, keys)
    
    def close(self) -> None:
        """Close the database connection."""
        if self._connection and not self._connection.closed:
            self._connection.close()
            self._connection = None
