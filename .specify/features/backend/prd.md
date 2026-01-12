# 🧠 PRD: Backend Infrastructure (Serverless API Gateway + Lambda)

## tl;dr

Implement the core event-driven chat backend using AWS API Gateway (REST + WebSocket receive-only) with Lambda functions
for connection management, message ingestion, and fan-out delivery. Messages are sent via REST, persisted to DynamoDB,
and DynamoDB Streams trigger downstream Lambda workers for AI processing and real-time delivery.

---

## 🎯 Goals

- **Serverless Architecture**: Deploy backend as Lambda functions behind API Gateway, eliminating container
  orchestration overhead
- **WebSocket Support**: Provide real-time downstream delivery (receive-only for clients) via API Gateway WebSocket API
- **Channel-First Messaging**: Channels are the sole threading primitive (no conversations); every message is keyed by
  `channel_id`
- **REST API**: Expose REST endpoints for sending messages, message history, channel management, and health checks
- **Event-Driven Processing**: Use DynamoDB Streams to automatically trigger AI agent and delivery workers
- **Connection Management**: Track active WebSocket connections in DynamoDB for targeted message delivery
- **Operational Simplicity**: Minimize infrastructure management with fully managed AWS services

## 👤 User Stories

- As a **client**, I want to establish a WebSocket connection and receive real-time messages for my subscribed channels
- As a **client**, I want to send messages via REST and have them persisted and processed atomically
- As a **client**, I want to query message history via REST API
- As an **AI agent worker**, I want to receive user messages from DynamoDB Streams and generate responses
- As a **delivery worker**, I want to receive all message events and broadcast them to active WebSocket connections
- As a **system**, I need to track which WebSocket connections are active and which channels they subscribe to
- As a **developer**, I want to deploy the backend using SAM templates with minimal configuration

## 🔄 Message Flow

### REST Message Flow

```text
1. Client sends message via REST (API Gateway REST)
   ↓
2. REST Lambda validates and writes to `chat_events` DynamoDB table
   ↓
3. DynamoDB Stream captures INSERT event
   ↓
4. Stream triggers chat-agent-worker (generates AI response) and chat-delivery-worker
   ↓
5. Delivery worker queries connections table for subscribers
   ↓
6. Delivery worker uses API Gateway v2 Management API to push to each active WebSocket connection
```

### Connection Management Flow (WebSocket receive-only)

```text
1. Client connects → OnConnect Lambda
   ↓
2. Extract userId 
   ↓
3. Store connection record
   ↓
4. Client disconnects → OnDisconnect Lambda
   ↓
5. Delete connection record from DynamoDB
```

### Message Delivery Flow

```text
1. Delivery worker receives stream event (from chat_events table)
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
- `sendmessage` - Handle incoming messages - triggered by delivery worker using event bus

### REST API Endpoints

- `GET /channels/{channel_id}/messages` - Query message history
- `POST /channels/{channel_id}/messages` - Send message via REST

### Lambda Functions

1. **OnConnect** - Validates JWT token, stores connection metadata in DynamoDB
2. **OnDisconnect** - Removes connection record from DynamoDB
3. **SendMessageFunction** - Broadcast messages using websockets
4. **SendChannelMessages** - Validates and persists messages to DynamoDB, triggers event stream
5. **GetChannelMessages** - Retrieves paginated message history from DynamoDB

### Integration with Event Bus

The backend integrates with the DynamoDB event bus:

1. **Message Write**: `SendMessage` Lambda writes to `chat_events` table
2. **Stream Trigger**: DynamoDB Stream captures the write event
3. **Consumer Processing**:
    - `chat-agent-worker` Lambda processes user messages and generates AI responses
    - `chat-delivery-worker` Lambda broadcasts messages to active WebSocket connections
4. **Delivery**: Delivery worker uses API Gateway Management API to send messages to specific connections

## 📚 References

- [DynamoDB Event Bus PRD](../DDB-eventbus/prd.md)
- [Technical Decision: Why API Gateway](../../technical-decisions/why-apigateway.md)
- [Technical Decision: Why DynamoDB](../../technical-decisions/why-dynamodb.md)
