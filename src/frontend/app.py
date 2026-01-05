import json
import os
import uuid

import requests
import streamlit as st

# Try relative or absolute imports depending on how the app is run
try:
    from websocket_client import WebSocketClient
except (ImportError, ModuleNotFoundError):
    from src.frontend.websocket_client import WebSocketClient

from streamlit.runtime.scriptrunner import add_script_run_ctx

# Configuration
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
WS_BASE_URL = os.getenv("WS_BASE_URL", API_BASE_URL.replace("http", "ws") + "/ws")

st.set_page_config(page_title="Scalable Chat", page_icon="💬", layout="wide")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "conversation_id" not in st.session_state:
    st.session_state.channel_id = "default-room"

if "ws_client" not in st.session_state:
    st.session_state.ws_client = None


def on_message(message_text):
    """Callback for when a new message is received via WebSocket."""
    print(f"DEBUG: on_message received: {message_text}", flush=True)
    try:
        try:
            data = json.loads(message_text)
            content = data.get("content", message_text)
            role = data.get("role", "assistant")
        except json.JSONDecodeError:
            content = message_text
            role = "assistant"
        
        print(f"DEBUG: Parsed content: {content}, role: {role}", flush=True)
        
        # Check if message already exists
        exists = any(m["content"] == content and m["role"] == role for m in st.session_state.messages)
        print(f"DEBUG: Message exists in state? {exists}", flush=True)
        
        if not exists:
            print("DEBUG: Appending message and requesting rerun", flush=True)
            st.session_state.messages.append({"role": role, "content": content, "id": str(uuid.uuid4())})
            st.rerun()
        else:
            print("DEBUG: Message skipped (duplicate)", flush=True)
    
    except Exception as e:
        print(f"ERROR in on_message: {e}", flush=True)
        st.error(f"Error processing message: {e}")


def start_ws_client():
    if st.session_state.ws_client:
        st.session_state.ws_client.stop()
    
    url = f"{WS_BASE_URL}/{st.session_state.channel_id}"
    client = WebSocketClient(url, on_message)
    add_script_run_ctx(client.thread)
    client.start()
    st.session_state.ws_client = client


# UI Header
st.title("💬 Scalable Chat Service")
st.caption("Real-time Multi-subscriber Sync via SNS/SQS & LocalStack")

# Sidebar
with st.sidebar:
    st.header("Settings")
    new_conv_id = st.text_input("Conversation ID", value=st.session_state.channel_id)
    
    if st.button("Join / Refresh") or new_conv_id != st.session_state.channel_id:
        st.session_state.channel_id = new_conv_id
        try:
            resp = requests.get(f"{API_BASE_URL}/conversations/{st.session_state.channel_id}/messages")
            if resp.status_code == 200:
                st.session_state.messages = [
                    {"role": m["role"], "content": m["content"], "id": m["id"]}
                    for m in resp.json()
                ]
            else:
                st.session_state.messages = []
        except Exception as e:
            st.error(f"Failed to fetch history: {e}")
        
        start_ws_client()
        st.rerun()
    
    st.divider()
    if st.session_state.ws_client:
        st.success(f"Connected to: {st.session_state.channel_id}")
    else:
        st.warning("Not connected. Click Join.")

# Display Chat
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat Input
if prompt := st.chat_input("Type your message..."):
    try:
        payload = {
            "conversation_id": st.session_state.channel_id,
            "content": prompt
        }
        resp = requests.post(f"{API_BASE_URL}/messages", json=payload)
        if resp.status_code != 200:
            st.error(f"Failed to send message: {resp.text}")
    except Exception as e:
        st.error(f"Error sending message: {e}")

# Initial connection
if st.session_state.ws_client is None or (
        hasattr(st.session_state.ws_client, "thread") and not st.session_state.ws_client.thread.is_alive()):
    # Only try to connect if we are NOT in a testing environment
    if os.getenv("STREAMLIT_TESTING") != "true":
        start_ws_client()
