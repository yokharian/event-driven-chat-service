# Data Access Layer (DAL) - Product Requirements

## Goals

Enable database-agnostic business logic that can seamlessly switch between DynamoDB and PostgreSQL without code changes.
Provide a consistent interface for data operations that simplifies testing, migration, and maintenance.

## User Stories

**As a developer**, I want to write business logic that works with any database, so I can switch between DynamoDB and
PostgreSQL without rewriting service code.

**As a developer**, I want to inject mock repositories in tests, so I can test business logic without connecting to a
real database.

**As a developer**, I want to migrate from DynamoDB to PostgreSQL gradually, so I can reduce vendor lock-in without a
big-bang migration.

**As a developer**, I want services to default to DynamoDB, so existing code continues working without changes.

## Core Components

### IRepository Interface

Abstract contract defining five core operations:

- `create(item)` - Create new records
- `get_by_key(**keys)` - Retrieve by primary key
- `get_list()` - Retrieve all records
- `update(params, **keys)` - Update existing records
- `delete(**keys)` - Delete records

All methods return dictionaries, keeping the interface database-agnostic.

### Repository Implementations

**DynamoDBRepository** - Default implementation for DynamoDB:

- Auto-assigns UUID primary keys when enabled
- Handles DynamoDB-specific operations (scan, query, update expressions)
- Converts AWS exceptions to repository exceptions

**PostgreSQLRepository** - Alternative implementation for PostgreSQL:

- Auto-assigns UUID primary keys when enabled
- Handles SQL queries and transactions
- Serializes enum values automatically

### BaseService Pattern

Services inherit from `BaseService` which:

- Defaults to `DynamoDBRepository` if no repository is injected
- Accepts any `IRepository` implementation via dependency injection
- Keeps business logic database-agnostic

## How It Works

### Default Behavior

Services automatically use DynamoDB:

```python
class MessageService(BaseService):
    def __call__(self):
        messages = self.repository.get_list()  # Uses DynamoDB
        return messages
```

### Dependency Injection

Inject any repository for testing or migration:

```python
# Use PostgreSQL instead
postgres_repo = PostgreSQLRepository(
    table_name='messages',
    connection_string=settings.postgres_connection_string
)
service = MessageService(repository=postgres_repo)
```

### Testing

Create mock repositories that implement `IRepository`:

```python
class MockRepository(IRepository):
    def get_list(self):
        return [{'id': '1', 'name': 'Test Message'}]


service = MessageService(repository=MockRepository())
```

## Problems Solved

**Vendor Lock-in** - Business logic doesn't depend on DynamoDB-specific APIs. Switch databases by changing repository
instances.

**Testing Complexity** - Mock repositories eliminate need for test databases. Test business logic in isolation.

**Migration Pain** - Gradual migration possible. Run both databases in parallel, route traffic incrementally.

**Code Duplication** - Single interface eliminates duplicate CRUD logic across services.

## References

- Technical Decision: `.specify/decisions/technical-decisions-v2/why-data-access-layer.md`

