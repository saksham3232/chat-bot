import streamlit as st
from groq import Groq
from dotenv import load_dotenv
from datetime import datetime
import os

# === Utility Functions ===
def generate_chat_title(text, max_len=40):
    first_line = text.strip().split("\n")[0]
    return first_line if len(first_line) <= max_len else first_line[:max_len - 3] + "..."

def truncate_title(title, max_len=20):
    return title if len(title) <= max_len else title[:max_len - 3] + "..."

# === Load environment and Groq ===
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

# === Streamlit App ===
st.set_page_config(page_title="Groq Chatbot", page_icon="🥢")
st.title("🧠 Groq Chatbot (ChatGPT-like)")

# === Session State Initialization ===
if "groq_model" not in st.session_state:
    st.session_state.groq_model = "llama3-8b-8192"
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
if "is_new_chat" not in st.session_state:
    st.session_state.is_new_chat = True
if "edit_index" not in st.session_state:
    st.session_state.edit_index = -1

# === Sidebar: Controls & History ===
with st.sidebar:
    st.subheader("💬 Chat Controls")
    if st.button("➕ New Chat"):
        st.session_state.messages = []
        st.session_state.current_chat_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        st.session_state.is_new_chat = True
        st.rerun()

    st.subheader("🕒 Recent Chats")
    for i, chat in reversed(list(enumerate(st.session_state.chat_history))):
        col1, col2 = st.columns([0.8, 0.2])
        with col1:
            short_title = truncate_title(chat.get("title", chat["chat_id"]))
            if st.button(short_title, key=f"chat_{i}"):
                st.session_state.messages = chat["messages"]
                st.session_state.current_chat_id = chat["chat_id"]
                st.session_state.is_new_chat = False
                st.rerun()
        with col2:
            if st.button("🗑️", key=f"delete_{i}"):
                if st.session_state.current_chat_id == chat["chat_id"]:
                    st.session_state.messages = []
                    st.session_state.current_chat_id = ""
                del st.session_state.chat_history[i]
                st.rerun()

# === Display Chat Messages ===
for i, msg in enumerate(st.session_state.messages):
    if msg["role"] == "user":
        if st.session_state.edit_index == i:
            new_content = st.text_input("Edit your message:", value=msg["content"], key=f"edit_input_{i}")
            col1, col2 = st.columns([0.5, 0.5])
            with col1:
                if st.button("✅ Save Edit", key=f"save_{i}"):
                    # Save the edited message
                    st.session_state.messages[i]["content"] = new_content
                    st.session_state.messages = st.session_state.messages[:i + 1]
                    st.session_state.edit_index = -1

                    # Get assistant response for the edited prompt
                    full_response = ""
                    try:
                        stream = client.chat.completions.create(
                            model=st.session_state.groq_model,
                            messages=[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages],
                            stream=True
                        )
                        with st.chat_message("assistant"):
                            response_container = st.empty()
                            for chunk in stream:
                                delta = chunk.choices[0].delta
                                if delta and delta.content:
                                    full_response += delta.content
                                    response_container.markdown(full_response)
                    except Exception as e:
                        full_response = f"❌ Error: {e}"
                        st.error(full_response)

                    st.session_state.messages.append({"role": "assistant", "content": full_response})
                    st.rerun()
            with col2:
                if st.button("❌ Cancel Edit", key=f"cancel_{i}"):
                    st.session_state.edit_index = -1
                    st.rerun()
        else:
            with st.chat_message("user"):
                st.markdown(msg["content"])
                if st.button("✏️ Edit", key=f"edit_{i}"):
                    st.session_state.edit_index = i
                    st.rerun()
    else:
        with st.chat_message("assistant"):
            st.markdown(msg["content"])

# === Chat Input & Assistant Response ===
if prompt := st.chat_input("What's on your mind?"):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    full_response = ""
    try:
        stream = client.chat.completions.create(
            model=st.session_state.groq_model,
            messages=[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages],
            stream=True
        )
        with st.chat_message("assistant"):
            response_container = st.empty()
            for chunk in stream:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    full_response += delta.content
                    response_container.markdown(full_response)
    except Exception as e:
        full_response = f"❌ Error: {e}"
        st.error(full_response)

    st.session_state.messages.append({"role": "assistant", "content": full_response})

    if st.session_state.is_new_chat:
        chat_title = generate_chat_title(prompt)
        st.session_state.chat_history.append({
            "chat_id": st.session_state.current_chat_id,
            "title": chat_title,
            "messages": st.session_state.messages.copy()
        })
        st.session_state.is_new_chat = False
        st.rerun()