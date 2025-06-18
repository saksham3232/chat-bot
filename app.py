import streamlit as st
from groq import Groq
from dotenv import load_dotenv
import os
from datetime import datetime

# Load environment variables from .env file
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Initialize Groq client
client = Groq(api_key=GROQ_API_KEY)

st.set_page_config(page_title="Groq Chatbot", page_icon="🤖")
st.title("🧠 Groq Chatbot (ChatGPT-like)")

# Initialize session state
if "groq_model" not in st.session_state:
    st.session_state["groq_model"] = "llama3-8b-8192"

if "messages" not in st.session_state:
    st.session_state["messages"] = []

if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

if "current_chat_id" not in st.session_state:
    st.session_state["current_chat_id"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Sidebar: New Chat & Chat History
with st.sidebar:
    st.subheader("💬 Chat Controls")

    # New chat button
    if st.button("➕ New Chat"):
        if st.session_state["messages"]:
            st.session_state["chat_history"].append({
                "chat_id": st.session_state["current_chat_id"],
                "messages": st.session_state["messages"]
            })
        st.session_state["messages"] = []
        st.session_state["current_chat_id"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.rerun()

    st.subheader("🕑 Recent Chats")

    for i, chat in reversed(list(enumerate(st.session_state["chat_history"]))):
        col1, col2 = st.columns([0.75, 0.25])
        with col1:
            if st.button(chat["chat_id"], key=f"chat_{i}"):
                st.session_state["messages"] = chat["messages"]
                st.session_state["current_chat_id"] = chat["chat_id"]
                st.rerun()
        with col2:
            if st.button("🗑️", key=f"delete_{i}"):
                # If the currently open chat is the one being deleted
                if st.session_state["current_chat_id"] == chat["chat_id"]:
                    st.session_state["messages"] = []
                    st.session_state["current_chat_id"] = ""
                del st.session_state["chat_history"][i]
                st.rerun()


# Display previous messages
for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("What's on your mind?"):
    st.chat_message("user").markdown(prompt)
    st.session_state["messages"].append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        full_response = ""
        response_container = st.empty()

        try:
            stream = client.chat.completions.create(
                model=st.session_state["groq_model"],
                messages=[
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state["messages"]
                ],
                stream=True
            )

            for chunk in stream:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    full_response += delta.content
                    response_container.markdown(full_response)

        except Exception as e:
            full_response = f"❌ Error: {e}"
            st.error(full_response)

        st.session_state["messages"].append({"role": "assistant", "content": full_response})