# 🧠 PRD: Basic Frontend UI (Multi-Subscriber Testing)

## tl;dr

Create a lightweight frontend to validate the multi-user/multi-tab capabilities of the event-driven architecture using
AWS API Gateway WebSocket API.

---

## 🎯 Goals

- Provide a simple UI to send messages via REST API and receive chat messages via AWS API Gateway WebSocket API.
- Enable testing of multiple concurrent WebSocket subscribers on the same machine.
- Visualize real-time delivery of AI responses across different sessions.
- Validate the serverless WebSocket architecture with multiple client connections.
- Demonstrate the hybrid architecture: REST API for sending, WebSocket for receiving real-time broadcasts.

## 👤 User Stories

- As a **user**, I want to send messages via REST API and receive messages (and AI replies) in real-time via WebSocket.
- As a **tester**, I want to open multiple browser tabs and verify that messages sent from one tab are broadcast to all
  active WebSocket connections.
- As a **developer**, I want to test the connection management, REST API message sending, and WebSocket broadcast
  delivery flows.

## 🧱 Technical Requirements

- **Framework**: Streamlit (Python-based UI).
- **Features**:
    - Input field for WebSocket API endpoint URL (wss://) or environment variable configuration.
    - Connection status indicator (connected/disconnected).
    - Message history display with sender information.
    - Chat input field to send messages via REST API.
    - REST API endpoint configuration for message sending.
- **WebSocket Logic** (Receive Only):
    - Connect to AWS API Gateway WebSocket endpoint (wss://{api-id}.execute-api.{region}.amazonaws.com/{stage}).
    - Handle connection lifecycle: $connect, $disconnect events.
    - Handle incoming messages and update local state.
    - Implement reconnection logic for dropped connections.
    - **Note**: WebSocket is used exclusively for receiving real-time broadcasts. Messages are NOT sent via WebSocket.
- **REST API Integration**:
    - Send messages via `POST /messages` or `POST /conversations/{id}/messages` endpoints.
    - Handle API responses and errors appropriately.
    - Messages sent via REST API are processed by the backend and broadcast to all WebSocket connections.
- **Testing Capability**: Should be easy to open in multiple browser windows to verify that messages are delivered to
  all subscribers.

## 🔄 Message Flow

1. User enters WebSocket endpoint URL and clicks "Connect".
2. Frontend establishes WebSocket connection → API Gateway triggers `$connect` route.
3. User sends message → Frontend sends message via **REST API** (`POST /messages` or
   `POST /conversations/{id}/messages`) → Backend processes message.
4. Backend publishes message to SNS → Delivery worker broadcasts to all WebSocket connections.
5. Frontend receives broadcast message via WebSocket and displays it in the chat history.
6. User disconnects → API Gateway triggers `$disconnect` route.

**Important**: Messages are sent via **REST API ONLY**. WebSocket is used exclusively for receiving real-time message
broadcasts. The WebSocket `sendmessage` route is not used for sending messages.

## 📚 References

- [Backend PRD](../backend/prd.md)
- [WebSocket API Implementation](../../../src/websocket_api/README.md)
