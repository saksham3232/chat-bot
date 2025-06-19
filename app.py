import streamlit as st
from streamlit_oauth import OAuth2Component
from google.oauth2 import id_token
from google.auth.transport import requests as grequests
from datetime import datetime
import os
from dotenv import load_dotenv
from groq import Groq
import firebase_admin
from firebase_admin import credentials, firestore

# === Load environment ===
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

# === Firebase Init ===
if "firebase_app" not in st.session_state:
    cred = credentials.Certificate(st.secrets["firebase"])
    firebase_admin.initialize_app(cred)
    st.session_state.firebase_app = True

db = firestore.client()

# === Google OAuth Setup ===
GOOGLE_CLIENT_ID = st.secrets["google_oauth"]["client_id"]
GOOGLE_CLIENT_SECRET = st.secrets["google_oauth"]["client_secret"]
REDIRECT_URI = st.secrets["google_oauth"]["redirect_uri"]

oauth = OAuth2Component(
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    authorize_endpoint="https://accounts.google.com/o/oauth2/v2/auth",
    token_endpoint="https://oauth2.googleapis.com/token",
    revoke_endpoint="https://oauth2.googleapis.com/revoke",
    scope="openid email profile",
    redirect_uri=REDIRECT_URI,
)

if "user_email" not in st.session_state:
    st.session_state.user_email = None

# === Login Flow ===
if st.session_state.user_email is None:
    result = oauth.authorize_button("Login with Google")
    if result and "token" in result:
        try:
            idinfo = id_token.verify_oauth2_token(
                result["token"]["id_token"], grequests.Request(), GOOGLE_CLIENT_ID
            )
            st.session_state.user_email = idinfo["email"]
            st.rerun()
        except Exception as e:
            st.error(f"Google Login failed: {e}")
else:
    st.sidebar.success(f"Logged in as {st.session_state.user_email}")
    if st.sidebar.button("Logout"):
        st.session_state.user_email = None
        st.session_state.clear()
        st.rerun()

    username = st.session_state.user_email

    # === Helper Functions ===
    def generate_chat_title(text, max_len=40):
        first_line = text.strip().split("\n")[0]
        return first_line if len(first_line) <= max_len else first_line[:max_len - 3] + "..."

    def truncate_title(title, max_len=20):
        return title if len(title) <= max_len else title[:max_len - 3] + "..."

    def save_chat_to_firebase(user, chat_id, title, messages):
        db.collection("chats").document(f"{user}_{chat_id}").set({
            "user": user,
            "chat_id": chat_id,
            "title": title,
            "messages": messages,
            "updated_at": datetime.utcnow()
        })

    def load_chats_for_user(user):
        docs = db.collection("chats").where("user", "==", user).stream()
        return [doc.to_dict() for doc in docs]

    def delete_chat_from_firebase(user, chat_id):
        db.collection("chats").document(f"{user}_{chat_id}").delete()

    # === Session State ===
    if "groq_model" not in st.session_state:
        st.session_state.groq_model = "llama3-8b-8192"
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = load_chats_for_user(username)
    if "current_chat_id" not in st.session_state:
        st.session_state.current_chat_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    if "is_new_chat" not in st.session_state:
        st.session_state.is_new_chat = True
    if "edit_index" not in st.session_state:
        st.session_state.edit_index = -1
    if "edit_mode" not in st.session_state:
        st.session_state.edit_mode = False

    # === Page Config ===
    st.set_page_config(page_title="Chatbot", page_icon="🤖")
    st.title(f"🤖 Chatbot - Welcome {username}")

    # === Sidebar ===
    with st.sidebar:
        if st.button("+ New Chat"):
            st.session_state.messages = []
            st.session_state.current_chat_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            st.session_state.is_new_chat = True
            st.session_state.edit_index = -1
            st.rerun()

        st.session_state.edit_mode = st.checkbox("🛠️ Enable Edit Mode", value=st.session_state.edit_mode)

        st.subheader("🕒 Recent Chats")
        for i, chat in reversed(list(enumerate(st.session_state.chat_history))):
            col1, col2 = st.columns([0.8, 0.2])
            with col1:
                if st.button(truncate_title(chat["title"]), key=f"chat_{i}"):
                    st.session_state.messages = chat["messages"]
                    st.session_state.current_chat_id = chat["chat_id"]
                    st.session_state.is_new_chat = False
                    st.session_state.edit_index = -1
                    st.rerun()
            with col2:
                if st.button("🗑️", key=f"del_{i}"):
                    delete_chat_from_firebase(username, chat["chat_id"])
                    del st.session_state.chat_history[i]
                    st.rerun()

    # === Chat History ===
    for i, msg in enumerate(st.session_state.messages):
        if msg["role"] == "user":
            if st.session_state.edit_mode and st.session_state.edit_index == i:
                new_input = st.text_input("Edit your message:", value=msg["content"], key=f"edit_{i}")
                if st.button("✅ Save", key=f"save_{i}"):
                    st.session_state.messages[i]["content"] = new_input
                    st.session_state.messages = st.session_state.messages[:i + 1]
                    st.session_state.edit_index = -1
                    full_response = ""
                    try:
                        stream = client.chat.completions.create(
                            model=st.session_state.groq_model,
                            messages=[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages],
                            stream=True
                        )
                        with st.chat_message("assistant"):
                            container = st.empty()
                            for chunk in stream:
                                delta = chunk.choices[0].delta
                                if delta and delta.content:
                                    full_response += delta.content
                                    container.markdown(full_response)
                    except Exception as e:
                        full_response = f"❌ Error: {e}"
                        st.error(full_response)
                    st.session_state.messages.append({"role": "assistant", "content": full_response})
                    save_chat_to_firebase(username, st.session_state.current_chat_id, generate_chat_title(new_input), st.session_state.messages.copy())
                    st.session_state.chat_history = load_chats_for_user(username)
                    st.rerun()
                elif st.button("❌ Cancel", key=f"cancel_{i}"):
                    st.session_state.edit_index = -1
                    st.rerun()
            else:
                with st.chat_message("user"):
                    st.markdown(msg["content"])
                    if st.session_state.edit_mode and st.button("✏️ Edit", key=f"edit_btn_{i}"):
                        st.session_state.edit_index = i
                        st.rerun()
        else:
            with st.chat_message("assistant"):
                st.markdown(msg["content"])

    # === Chat Input ===
    if prompt := st.chat_input("Ask anything..."):
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
                container = st.empty()
                for chunk in stream:
                    delta = chunk.choices[0].delta
                    if delta and delta.content:
                        full_response += delta.content
                        container.markdown(full_response)
        except Exception as e:
            full_response = f"❌ Error: {e}"
            st.error(full_response)

        st.session_state.messages.append({"role": "assistant", "content": full_response})

        save_chat_to_firebase(username, st.session_state.current_chat_id, generate_chat_title(prompt), st.session_state.messages.copy())
        if st.session_state.is_new_chat:
            st.session_state.is_new_chat = False
        st.session_state.chat_history = load_chats_for_user(username)
        st.rerun()