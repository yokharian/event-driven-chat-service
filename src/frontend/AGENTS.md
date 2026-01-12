Streamlit UI in `src/frontend/app.py` connects to a WebSocket endpoint for live chat while sending outbound messages
over the REST API.

WebSocket to receive messages
---

- opens a WebSocket
- WebSocket URL switches automatically between local and Docker targets based on `IS_DOCKERIZED`.

HTTP message send
---

- The message is sent to the REST API
- initial history is fetched through `requests.get(f"{API_BASE_URL}/channels/{channel}/messages")` and loaded into state
  before the WebSocket consumer starts.
- REST base URL resolves via `APIGW_REST_API_ID` or an SSM parameter (`API_ID_SSM_PARAM`) for LocalStack.
