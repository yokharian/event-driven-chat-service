# Data Access Layer (DAL) Pattern

This module implements the Data Access Layer pattern, which provides a database-agnostic interface for data operations.
This allows you to migrate between different databases (DynamoDB, PostgreSQL, etc.) without changing your business
logic.

## Architecture

```
Business Layer (Services)
    ↓
IRepository (Abstract Interface/Contract)
    ↓
Repository Implementations (DynamoDBRepository, PostgreSQLRepository)
    ↓
Database (DynamoDB, PostgreSQL, etc.)
```

## Usage

### Default Usage (DynamoDB)

Services automatically use DynamoDB by default:

```python
from services.base import BaseService


class MyService(BaseService):
    def __call__(self):
        # Uses DynamoDBRepository automatically
        items = self.repository.get_list()
        return items
```

### Dependency Injection

You can inject any repository implementation for testing or migration:

```python
from services.base import BaseService
from commons.dal import PostgreSQLRepository

# Inject PostgreSQL repository
postgres_repo = PostgreSQLRepository(
    table_name='messages',
    connection_string='postgresql://user:pass@localhost/db'
)

service = MyService(repository=postgres_repo)
```

### Migrating from DynamoDB to PostgreSQL

1. **Update your service to accept a repository:**

```python
from services.base import BaseService
from commons.dal import IRepository


class MyService(BaseService):
    def __call__(self):
        # Works with any IRepository implementation
        items = self.repository.get_list()
        return items
```

2. **Create the PostgreSQL repository:**

```python
from commons.dal import PostgreSQLRepository

postgres_repo = PostgreSQLRepository(
    table_name='messages',
    connection_string=settings.postgres_connection_string
)
```

3. **Use dependency injection:**

```python
# In your Lambda handler or factory
service = MyService(repository=postgres_repo)
```

### Testing with Mock Repositories

You can easily create mock repositories for testing:

```python
from unittest.mock import Mock
from commons.dal import IRepository


class MockRepository(IRepository):
    def create(self, item):
        return {**item, 'id': 'test-id'}
    
    def get_by_key(self, *, raise_not_found=True, **keys):
        return {'id': keys.get('id'), 'name': 'Test Engine'}
    
    def get_list(self):
        return [{'id': '1'}, {'id': '2'}]
    
    def update(self, params, **keys):
        pass
    
    def delete(self, **keys):
        pass


# Use in tests
service = MyService(repository=MockRepository())
```

## Available Implementations

- **DynamoDBRepository**: Full DynamoDB implementation with auto-key assignment
- **PostgreSQLRepository**: Basic PostgreSQL implementation (can be extended)

## Interface Methods

All repository implementations must provide:

- `create(item: Dict) -> Dict`: Create a new item
- `get_by_key(*, raise_not_found: bool = True, **keys) -> Optional[Dict]`: Get item by primary key
- `get_list() -> List[Dict]`: Get all items
- `update(params: Dict, **keys) -> None`: Update an item
- `delete(**keys) -> None`: Delete an item

## Backward Compatibility

The old `TableRepository` class is still available as an alias to `DynamoDBRepository` for backward compatibility.
However, new code should use `DynamoDBRepository` or the `IRepository` interface.
