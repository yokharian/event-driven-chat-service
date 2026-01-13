# Simple WebSockets Chat App

![diagram.svg](diagram.svg)

A WebSocket chat application using AWS API Gateway WebSocket API and Lambda functions, refactored to use the Data Access
Layer (DAL) pattern.

## Architecture

This application consists of three Lambda functions:

- **onconnect**: Handles WebSocket connection events, stores connection IDs in DynamoDB
- **ondisconnect**: Handles WebSocket disconnection events, removes connection IDs from DynamoDB
- **sendmessage**: Broadcasts messages to all connected WebSocket clients
- **local_server.py**: Local FastAPI-based WebSocket gateway that emulates API Gateway WebSocket behavior for local/dev

## Data Access Layer (DAL)

All Lambda functions use the `DynamoDBRepository` from `commons.dal` following the repository pattern:

- **Abstraction**: Business logic is decoupled from DynamoDB-specific operations
- **Consistency**: All database operations use the same interface
- **Testability**: Repository can be easily mocked for testing
- **Error Handling**: Uses standardized exceptions (`RepositoryError`, `ObjectNotFoundError`)

### Repository Configuration

Each function initializes the repository with:

```python
repository = DynamoDBRepository(
    table_name=os.environ.get("TABLE_NAME"),
    table_hash_keys=["connectionId"],
    dynamodb_endpoint_url=os.environ.get("DYNAMODB_ENDPOINT_URL"),  # Optional for LocalStack
    key_auto_assign=False,  # connectionId comes from API Gateway
)
```

## Dependencies

Each Lambda function requires:

- `boto3>=1.35.0` - AWS SDK
- `pydantic>=2.0.0` - Data validation
- `pydantic-settings>=2.0.0` - Settings management
- `aws-lambda-powertools>=2.0.0` - Lambda utilities and logging

The `commons` package (shared across the project) is included during the build process.

## Building and Deploying

### Prerequisites

- AWS SAM CLI installed
- Python 3.12+
- `uv` package manager (recommended) or `pip`

### Build Process

The Makefiles in each function directory automatically copy the `commons` package during `sam build`:

```bash
# Build the SAM application
sam build

# Deploy to AWS
sam deploy --guided
```

### Local Development with LocalStack

For local development with LocalStack, set the `DYNAMODB_ENDPOINT_URL` environment variable:

```bash
export DYNAMODB_ENDPOINT_URL=http://localhost:4566
```

### Local WebSocket server (no API Gateway required)

`local_server.py` spins up a local FastAPI server that mimics API Gateway WebSocket API (useful because WebSockets are a
paid feature in LocalStack).

```bash
export TABLE_NAME=connections
export DYNAMODB_ENDPOINT_URL=http://localhost:4566
export AWS_REGION=us-east-1
export WS_PORT=8080  # optional

python -m src.websocket_api.local_server
```

Then open `http://localhost:8080/` for the test client or connect to `ws://localhost:8080/ws`.

## Environment Variables

- `TABLE_NAME`: DynamoDB table name (required)
- `AWS_REGION`: AWS region (defaults to `us-east-1`)
- `DYNAMODB_ENDPOINT_URL`: Optional endpoint URL for LocalStack/testing

## References

- See `commons/dal/` for repository interface and implementations
