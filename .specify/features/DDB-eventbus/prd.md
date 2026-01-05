# 🧠 PRD: DynamoDB Event Bus (Streams-Based Pub-Sub)

## tl;dr

Implement a unified data store and event bus using DynamoDB with Streams, eliminating dual-write complexity while
providing atomic message persistence and automatic event distribution to Lambda consumers. This architecture serves as
the source of truth for chat messages and enables event-driven processing for AI responses and real-time delivery.

---

## 🎯 Goals

- **Atomic Writes**: Eliminate dual-write risks by coupling data persistence and event generation in a single operation
- **Event-Driven Processing**: Automatically trigger downstream consumers (AI agent, delivery worker) via DynamoDB
  Streams
- **Exactly-Once Semantics**: Achieve deterministic message processing using idempotency keys and conditional writes
- **Operational Simplicity**: Minimize infrastructure complexity by using managed AWS services (DynamoDB, Streams,
  Lambda)
- **Ordering Guarantees**: Maintain message ordering per conversation/channel using partition key + sort key design

## 👤 User Stories

- As a **backend service**, I want to write a message to DynamoDB and have it automatically trigger event processing
  without separate publish operations
- As an **AI agent worker**, I want to receive user messages from the stream, generate responses, and write them back
  atomically
- As a **delivery worker**, I want to receive all message events and broadcast them to active WebSocket connections
- As a **system**, I need to ensure messages are never duplicated even if Lambda retries occur
- As a **developer**, I want to query message history directly from the same table that generates events

## 🔄 Event Flow

### User Message Flow

```
1. User sends message via WebSocket/REST
   ↓
2. Backend API writes to DynamoDB (channel_id, ts, event_id, role=user, content)
   ↓
3. DynamoDB Stream captures INSERT event
   ↓
4. Chatbot Consumer Lambda triggered
   ↓
5. Lambda processes message, calls LLM
   ↓
6. Lambda writes AI response to DynamoDB (role=ai, content=response)
   ↓
7. DynamoDB Stream captures new INSERT event
   ↓
8. Delivery Consumer Lambda triggered
   ↓
9. Lambda broadcasts to all WebSocket connections for channel_id
```

### Idempotency Flow

```
1. Backend receives message with potential duplicate event_id
   ↓
2. Attempt conditional write: "event_id does not exist"
   ↓
3a. If event_id new → Write succeeds, stream event generated
3b. If event_id exists → Write rejected (ConditionalCheckFailedException)
   ↓
4. Return success to client (idempotent operation)
```

## 🧱 Core Components

### DynamoDB Table

**Table Name**: `chat-events`

**Key Schema**:

- **Partition Key**: `channel_id` (String) - Chat channel/room identifier
- **Sort Key**: `ts` (Number) - Unix timestamp for chronological ordering

**Message Attributes**:

- `event_id` (String) - Idempotency key (ULID/UUID) for exactly-once processing
- `message_id` (String) - Public identifier
- `sender_id` (String) - User ID or system ID
- `role` (String) - Message author type: `user`, `ai`, or `system`
- `content` (String) - Message body/text
- `content_type` (String) - Content format: `text` or `markdown`
- `created_at_iso` (String) - ISO8601 timestamp
- `metadata` (Map) - Optional arbitrary metadata

### DynamoDB Streams

- Stream enabled with `NEW_AND_OLD_IMAGES` view type
- Automatically triggers Lambda consumers on table changes
- Retention period: ~24 hours (AWS default)

### Lambda Consumer Functions

#### 1. Chatbot Consumer (`chat-agent-worker`)

- Processes user messages from the stream (filters for `role=user`)
- Calls LLM service to generate AI responses
- Writes AI response back to DynamoDB (triggers new stream event)
- Uses `event_id` for idempotency to prevent duplicate processing

#### 2. Delivery Consumer (`chat-delivery-worker`)

- Receives all message events (user, AI, system) from the stream
- Identifies active WebSocket connections for the `channel_id`
- Broadcasts messages to connected clients via API Gateway Management API

### Data Access Patterns

**Write Path**:

1. Backend API receives message via REST/WebSocket
2. Generate `event_id` (ULID/UUID) for idempotency
3. Write to DynamoDB with conditional write (check `event_id` doesn't exist)
4. DynamoDB Stream automatically generates event
5. Lambda consumers triggered asynchronously

**Read Path**:

1. Query by `channel_id` (partition key) to get all messages for a conversation
2. Use `ts` (sort key) for chronological ordering
3. Implement cursor-based pagination using `ts` as cursor

**Event Processing Path**:

1. DynamoDB Stream captures table change
2. Lambda function invoked with batch of stream records
3. Process each record (filter, transform, act)
4. Write results back to DynamoDB if needed (triggers new stream event)
5. On failure: retry with exponential backoff, eventually send to DLQ

## 📚 References

- [Technical Decision: Why DynamoDB](./../../technical-decisions/why-dynamodb.md)
- [Technical Decision: Why Not SNS+SQS](../../technical-decisions/why-not-sns-sqs.md)
- [Table Schema Diagram](./table-schema.puml)
- [Architecture Diagram](./diagram.puml)
