# 🧠 PRD: Backend Infrastructure (Serverless API Gateway + Lambda)

## tl;dr

Implement the core event-driven chat backend using AWS API Gateway (WebSocket + REST) with Lambda functions for
connection management and message handling. Messages are persisted to DynamoDB, which triggers downstream Lambda workers
via DynamoDB Streams for AI processing and real-time delivery.

---

## 🎯 Goals

- **Serverless Architecture**: Deploy backend as Lambda functions behind API Gateway, eliminating container
  orchestration overhead
- **WebSocket Support**: Provide real-time bidirectional communication via API Gateway WebSocket API
- **REST API**: Expose REST endpoints for message history, channel management, and health checks
- **Event-Driven Processing**: Use DynamoDB Streams to automatically trigger AI agent and delivery workers
- **Connection Management**: Track active WebSocket connections in DynamoDB for targeted message delivery
- **Operational Simplicity**: Minimize infrastructure management with fully managed AWS services

## 👤 User Stories

- As a **client**, I want to establish a WebSocket connection and receive real-time messages for my subscribed channels
- As a **client**, I want to send messages via WebSocket and have them persisted and processed atomically
- As a **client**, I want to query message history via REST API
- As an **AI agent worker**, I want to receive user messages from DynamoDB Streams and generate responses
- As a **delivery worker**, I want to receive all message events and broadcast them to active WebSocket connections
- As a **system**, I need to track which WebSocket connections are active and which channels they subscribe to
- As a **developer**, I want to deploy the backend using SAM templates with minimal configuration

## 🔄 Message Flow

### WebSocket Message Flow

```
1. Client establishes WebSocket connection
   ↓
2. API Gateway triggers $connect route → OnConnect Lambda
   ↓
3. OnConnect validates JWT, stores connection in DynamoDB
   ↓
4. Client sends message via WebSocket (sendmessage route)
   ↓
5. API Gateway triggers sendmessage route → SendMessage Lambda
   ↓
6. SendMessage validates message, writes to chat-events table
   ↓
7. DynamoDB Stream captures INSERT event
   ↓
8. Stream triggers chat-agent-worker (generates AI response)
   ↓
9. Stream triggers chat-delivery-worker (broadcasts to connections)
   ↓
10. Delivery worker uses API Gateway Management API to send to clients
```

### Connection Management Flow

```
1. Client connects → OnConnect Lambda
   ↓
2. Extract userId and channelIds from JWT token
   ↓
3. Store connection record: {connectionId, userId, channelIds, ttl}
   ↓
4. Client disconnects → OnDisconnect Lambda
   ↓
5. Delete connection record from DynamoDB
```

### Message Delivery Flow

```
1. Delivery worker receives stream event (from chat-events table)
   ↓
2. Query connections table for channel_id subscribers
   ↓
3. For each matching connection:
   - Use API Gateway Management API to send message
   - Handle GoneException (stale connection) → delete from table
   ↓
4. Log delivery success/failure
```

## 🧱 Core Components

### WebSocket API Routes

- `$connect` - Handle new WebSocket connections
- `$disconnect` - Handle WebSocket disconnections
- `sendmessage` - Handle incoming messages from clients

### REST API Endpoints

- `GET /channels/{channel_id}/messages` - Query message history
- `GET /channels` - List available channels
- `GET /health` - Health check endpoint
- `POST /channels/{channel_id}/messages` - Send message via REST (alternative to WebSocket)

### Lambda Functions

1. **OnConnect** - Validates JWT token, stores connection metadata in DynamoDB
2. **OnDisconnect** - Removes connection record from DynamoDB
3. **SendMessage** - Validates and persists messages to DynamoDB, triggers event stream
4. **QueryMessages** - Retrieves paginated message history from DynamoDB

### Integration with Event Bus

The backend integrates with the DynamoDB event bus:

1. **Message Write**: `SendMessage` Lambda writes to `chat-events` table
2. **Stream Trigger**: DynamoDB Stream captures the write event
3. **Consumer Processing**:
    - `chat-agent-worker` Lambda processes user messages and generates AI responses
    - `chat-delivery-worker` Lambda broadcasts messages to active WebSocket connections
4. **Delivery**: Delivery worker uses API Gateway Management API to send messages to specific connections

## 📚 References

- [DynamoDB Event Bus PRD](./DDB-eventbus/prd.md)
- [Technical Decision: Why API Gateway](../technical-decisions/why-apigateway.md)
- [Technical Decision: Why DynamoDB](../technical-decisions/why-dynamodb.md)

