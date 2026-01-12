## Relevant Files

- `src/frontend/app.py` - Main Streamlit application entry point (includes aiohttp WebSocket consumer).
- `tests/frontend/test_app.py` - Integration tests for the Streamlit UI.
- `tests/frontend/test_websocket.py` - Unit tests for the WebSocket client logic.

### Notes

- Use `streamlit run src/frontend/app.py` to start the development server.
- Streamlit's state management (`st.session_state`) stores message history and connection status.
- WebSocket receive loop lives in `_chat_consumer` (aiohttp) invoked via `asyncio.run` when "Connect" is enabled.
- Multi-tab testing is achieved by opening the Streamlit URL in multiple browser windows/tabs.
- WebSocket endpoint format: `wss://{api-id}.execute-api.{region}.amazonaws.com/{stage}`
- **Message Sending**: Messages MUST be sent via REST API (`POST /messages`) ONLY. WebSocket is used exclusively for
  receiving real-time message broadcasts.
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
- [x] 2.0 UI Components (WebSocket Connection & Message Input)
    - [x] 2.1 Implement environment variable-based `WS_CONN`for WebSocket endpoint URL (wss://).
    - [x] 2.2 Implement connection status indicator (connected/disconnected/connecting).
    - [x] 2.3 Implement `st.chat_message` containers for displaying message history.
    - [x] 2.4 Implement `st.chat_input` for sending new messages.
    - [x] 2.5 Add connect/disconnect control to manage WebSocket connection.
- [ ] 3.0 WebSocket Client Implementation (Receive Only)
    - [x] 3.1 Provide WebSocket client logic. **NOTE: Implemented inline in `app.py` via `_chat_consumer`
      using `aiohttp` (no separate module).**
    - [x] 3.2 Establish WebSocket connection to API Gateway endpoint. **NOTE: `_chat_consumer` handles connect with
      heartbeat.**
    - [x] 3.4 Receive incoming messages and handle events. **NOTE: `_chat_consumer` parses text/binary and updates
      state.**
    - [ ] 3.5 Implement reconnection logic if the connection is dropped (exponential backoff). **NOTE: No
      reconnection/backoff; loop ends on error/close.**
- [x] 4.0 State Management & Real-time Updates
    - [x] 4.1 Initialize `st.session_state.messages` to store chat history.
    - [x] 4.2 Initialize connection tracking in session state. **NOTE: Uses `connected` boolean and `channel_id`.**
    - [x] 4.3 Receive WebSocket messages and update `st.session_state` via `_chat_consumer` loop (no separate thread).
    - [x] 4.4 Refresh UI by re-rendering placeholders on each message (no `st.rerun()` used).
    - [x] 4.5 Integrate message sending: UI Input -> REST API (`POST /channels/<channel>/messages`) -> Backend
      processes -> Delivery worker broadcasts via WebSocket -> UI Update.
- [ ] 5.0 Integration & Testing (Multi-tab validation)
    - [ ] 5.1 Deploy WebSocket API using SAM (`sam build && sam deploy`). **NOTE: Manual deployment task.**
    - [ ] 5.2 Get WebSocket endpoint URL from SAM outputs or API Gateway console. **NOTE: Manual task.**
    - [ ] 5.3 Launch Streamlit and open two browser tabs with the same WebSocket endpoint. **NOTE: Manual testing task.
      **
    - [ ] 5.4 Connect both tabs to the WebSocket API. **NOTE: Manual testing task.**
    - [ ] 5.5 Send a message from Tab A and verify it appears in Tab B (broadcast test). **NOTE: Manual testing task.**
    - [ ] 5.6 Verify connection management: disconnect Tab A, verify Tab B still receives messages. **NOTE: Manual
      testing task.**
    - [x] 5.7 Create basic integration tests in `tests/frontend/` for WebSocket client.
