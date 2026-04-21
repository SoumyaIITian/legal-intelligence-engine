import streamlit as st
import requests
import os
API_URL = os.getenv("API_URL", "http://localhost:8000/api/v1")



st.set_page_config(page_title="Legal Intelligence Demo", layout="centered")

# --- URL Parameter Routing ---
# If no tenant is provided in the URL, default to nero_law for testing
client_id = st.query_params.get("tenant", "nero_law")

# Wipe memory if the URL changes
if "active_client" not in st.session_state or st.session_state.active_client != client_id:
    st.session_state.messages = []
    st.session_state.active_client = client_id

# --- Clean, Locked-Down UI ---
st.title("⚖️ Firm Intelligence Portal")
st.caption(f"Secure Environment: Connected to proprietary knowledge base.")
st.divider()

# --- Render Chat History ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- Chat Input ---
if user_query := st.chat_input(f"Ask a specific operational question..."):
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