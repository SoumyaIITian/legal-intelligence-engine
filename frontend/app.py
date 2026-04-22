import streamlit as st
import requests
import os

API_URL = os.getenv("API_URL", "http://localhost:8000/api/v1")
HEALTH_URL = API_URL.replace("/api/v1", "/health")

st.set_page_config(page_title="Firm Intelligence Portal", layout="centered")

# --- Render Cold Start Handler ---
# Blocks the UI from loading until the backend responds
if "engine_awake" not in st.session_state:
    with st.spinner("Waking up secure inference engine... (This takes ~45 seconds on the first load)"):
        try:
            requests.get(HEALTH_URL, timeout=120)
            st.session_state.engine_awake = True
        except requests.exceptions.RequestException:
            st.error("Server connection timeout. Please refresh the page.")
            st.stop()

# --- URL Parameter Routing ---
client_id = st.query_params.get("tenant", "nero_law")

# Wipe memory if the URL changes
if "active_client" not in st.session_state or st.session_state.active_client != client_id:
    st.session_state.messages = []
    st.session_state.active_client = client_id

# --- Clean, Locked-Down UI ---
st.title("⚖️ Firm Intelligence Portal")
st.caption(f"Secure Environment: Connected to proprietary knowledge base for `{client_id}`.")
st.divider()

# --- Render Chat History ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- Chat Input ---
if user_query := st.chat_input("Ask a specific operational question..."):
    # 1. Display User Message
    st.session_state.messages.append({"role": "user", "content": user_query})
    with st.chat_message("user"):
        st.markdown(user_query)

    # 2. Call the Cloud API
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("*(Retrieving isolated firm context...)*")
        
        try:
            response = requests.post(
                f"{API_URL}/{client_id}/query", 
                json={
                    "query": user_query,
                    "chat_history": st.session_state.messages[:-1] 
                }
            )
            
            if response.status_code == 200:
                answer = response.json()["answer"]
                message_placeholder.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})
            else:
                message_placeholder.error("System error. Please try again.")
                
        except Exception as e:
            message_placeholder.error("Connection Error. Ensure backend is running.")
