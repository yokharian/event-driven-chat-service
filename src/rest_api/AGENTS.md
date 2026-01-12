## 🏗️ Tech Stack

- **Event Bus**: DynamoDB Streams trigger downstream Lambda workers (agent and delivery workers)

### Event Flow Pattern

- **REST Message**: Client sends messages via REST API → Lambda writes to `chat_events` DynamoDB table
- **DynamoDB Stream**: Stream captures INSERT events
- **Agent Worker (Lambda)**: Triggered by stream → processes user messages → generates AI response → writes back to
  table
- **Delivery Worker (Lambda)**: Triggered by stream → queries active connections → broadcasts via API Gateway
  Management API

---

## ✅ Required Patterns

1. **Error Handling** — Implement proper exception handling in services. Use `ObjectNotFoundError` from
   `commons.dynamodb.exceptions` for not found cases.
2. **CloudFormation Mandatory**: Resource creation is strictly limited to CloudFormation/SAM. Boto3 is only permitted
   for interacting with resources (e.g., DynamoDB operations through DAL, API Gateway Management API) or deploying
   stacks.
