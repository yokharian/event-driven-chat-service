## Relevant Files

- `src/frontend/app.py` - Main Streamlit application entry point.
- `src/frontend/websocket_client.py` - WebSocket client for connecting to AWS API Gateway WebSocket API.
- `src/frontend/schemas.py` - Pydantic models for frontend data (matching backend where necessary).
- `tests/frontend/test_app.py` - Integration tests for the Streamlit UI.
- `tests/frontend/test_websocket.py` - Unit tests for the WebSocket client logic.

### Notes

- Use `streamlit run src/frontend/app.py` to start the development server.
- Streamlit's state management (`st.session_state`) should be used to store message history and connection status.
- Since Streamlit is synchronous by nature, the WebSocket listener should likely run in a separate thread or use an
  async loop integrated with Streamlit's execution.
- Multi-tab testing is achieved by opening the Streamlit URL in multiple browser windows/tabs.
- WebSocket endpoint format: `wss://{api-id}.execute-api.{region}.amazonaws.com/{stage}`
- **Message Sending**: Messages MUST be sent via REST API (`POST /messages`) ONLY. WebSocket is used exclusively for receiving real-time message broadcasts.
- WebSocket route selection expression (`$request.body.action`) is not used since messages are not sent via WebSocket.

## Instructions for Completing Tasks

**IMPORTANT:** As you complete each task, you must check it off in this markdown file by changing `- [ ]` to `- [x]`.
This helps track progress and ensures you don't skip any steps.

Example:

- `- [ ] 1.1 Read file` → `- [x] 1.1 Read file` (after completing)

Update the file after completing each sub-task, not just after completing an entire parent task.

## Tasks

- [x] 1.0 Streamlit Scaffolding & Setup
    - [x] 1.1 Create `src/frontend/` directory.
    - [x] 1.2 Add `streamlit` and `websockets` (or `websocket-client`) to `pyproject.toml`.
    - [x] 1.3 Create a basic "Hello World" Streamlit app in `src/frontend/app.py`.
- [ ] 2.0 UI Components (WebSocket Connection & Message Input)
    - [ ] 2.1 Implement `st.text_input` for WebSocket endpoint URL (wss://). **NOTE: Currently uses environment variable `WS_BASE_URL` instead.**
    - [x] 2.2 Implement connection status indicator (connected/disconnected/connecting). **NOTE: Implemented in sidebar with success/warning messages.**
    - [x] 2.3 Implement `st.chat_message` containers for displaying message history.
    - [x] 2.4 Implement `st.chat_input` for sending new messages.
    - [x] 2.5 Add connect/disconnect button to manage WebSocket connection. **NOTE: "Join / Refresh" button exists, but no explicit disconnect button.**
- [ ] 3.0 WebSocket Client Implementation (Receive Only)
    - [x] 3.1 Create `src/frontend/websocket_client.py` using `websockets` or `websocket-client` library.
    - [x] 3.2 Implement `connect()` method to establish WebSocket connection to API Gateway endpoint. **NOTE: Connection happens in `_listen()` method, not a separate `connect()` method.**
    - [x] 3.4 Implement `listen()` method to receive incoming messages and handle connection events. **NOTE: Implemented as `_listen()` method.**
    - [ ] 3.5 Implement reconnection logic if the connection is dropped (exponential backoff). **NOTE: Has basic retry with 2s sleep, but no exponential backoff.**
- [x] 4.0 State Management & Real-time Updates
    - [x] 4.1 Initialize `st.session_state.messages` to store chat history.
    - [x] 4.2 Initialize `st.session_state.connection_status` to track WebSocket state. **NOTE: Uses `ws_client` in session_state to track connection.**
    - [x] 4.3 Create a background listener thread to receive WebSocket messages and update `st.session_state`.
    - [x] 4.4 Use `st.rerun()` (or the modern fragment/callback equivalent) to refresh the UI when new messages arrive.
    - [x] 4.5 Integrate message sending: UI Input -> REST API (`POST /messages`) -> Backend processes -> Delivery worker broadcasts via WebSocket -> UI Update. **NOTE: REST API is the only method for sending messages. WebSocket is used exclusively for receiving broadcasts.**
- [ ] 5.0 Integration & Testing (Multi-tab validation)
    - [ ] 5.1 Deploy WebSocket API using SAM (`sam build && sam deploy`). **NOTE: Manual deployment task.**
    - [ ] 5.2 Get WebSocket endpoint URL from SAM outputs or API Gateway console. **NOTE: Manual task.**
    - [ ] 5.3 Launch Streamlit and open two browser tabs with the same WebSocket endpoint. **NOTE: Manual testing task.**
    - [ ] 5.4 Connect both tabs to the WebSocket API. **NOTE: Manual testing task.**
    - [ ] 5.5 Send a message from Tab A and verify it appears in Tab B (broadcast test). **NOTE: Manual testing task.**
    - [ ] 5.6 Verify connection management: disconnect Tab A, verify Tab B still receives messages. **NOTE: Manual testing task.**
    - [x] 5.7 Create basic integration tests in `tests/frontend/` for WebSocket client.
