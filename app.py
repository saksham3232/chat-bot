import streamlit as st
from streamlit_cookies_manager import EncryptedCookieManager
import firebase_admin
from firebase_admin import credentials, firestore
from google.oauth2 import id_token
from google.auth.transport import requests as grequests
from datetime import datetime
from groq import Groq
from streamlit_oauth import OAuth2Component

# === Load Secrets ===
GROQ_API_KEY = st.secrets["GROQ"]["api_key"]
client = Groq(api_key=GROQ_API_KEY)

# === Firebase Initialization (robust for Streamlit reruns) ===
try:
    cred = credentials.Certificate(dict(st.secrets["firebase"]))
    firebase_admin.initialize_app(cred)
except ValueError:
    # Already initialized
    pass

db = firestore.client()

# === Google OAuth Setup ===
GOOGLE_CLIENT_ID = st.secrets["google_oauth"]["client_id"]
GOOGLE_CLIENT_SECRET = st.secrets["google_oauth"]["client_secret"]
REDIRECT_URI = st.secrets["google_oauth"]["redirect_uri"]

oauth = OAuth2Component(
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    authorize_endpoint="https://accounts.google.com/o/oauth2/v2/auth",
    token_endpoint="https://oauth2.googleapis.com/token"
)

# === Cookie Manager Initialization (robust, session-only cookies) ===
cookies = EncryptedCookieManager(
    prefix="",
    password=st.secrets.get("COOKIE_PASSWORD", "your-default-password"),
)
if not cookies.ready():
    st.stop()  # Wait until cookies are ready!

# === Session Initialization ===
if "user_email" not in st.session_state or not st.session_state.user_email:
    cookie_email = cookies.get("user_email")
    if cookie_email:
        st.session_state.user_email = cookie_email
    else:
        st.session_state.user_email = None
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
if "edit_mode" not in st.session_state:
    st.session_state.edit_mode = False

# === Utility Functions ===
def generate_chat_title(text, max_len=40):
    first_line = text.strip().split("\n")[0]
    return first_line if len(first_line) <= max_len else first_line[:max_len - 3] + "..."

def truncate_title(title, max_len=20):
    return title if len(title) <= max_len else title[:max_len - 3] + "..."

def save_chat():
    doc_id = f"{st.session_state.user_email}_{st.session_state.current_chat_id}"
    db.collection("chats").document(doc_id).set({
        "user": st.session_state.user_email,
        "chat_id": st.session_state.current_chat_id,
        "title": generate_chat_title(st.session_state.messages[0]["content"]) if st.session_state.messages else "New Chat",
        "messages": st.session_state.messages,
        "updated_at": datetime.utcnow()
    })

@st.cache_data
def load_chats(user_email):
    docs = db.collection("chats").where("user", "==", user_email).stream()
    return [doc.to_dict() for doc in docs]

def delete_chat(chat_id):
    doc_id = f"{st.session_state.user_email}_{chat_id}"
    db.collection("chats").document(doc_id).delete()

# === Login Page ===
if st.session_state.user_email is None:
    st.set_page_config(page_title="Login", layout="centered")
    st.markdown("<h2 style='text-align:center;'>🔐 Welcome to the Chatbot</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;'>Please login with Google to continue</p>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        result = oauth.authorize_button(
            "Login with Google",
            redirect_uri=REDIRECT_URI,
            scope="openid email profile"
        )

    if result and "token" in result:
        try:
            idinfo = id_token.verify_oauth2_token(result["token"]["id_token"], grequests.Request(), GOOGLE_CLIENT_ID)
            st.session_state.user_email = idinfo["email"]
            # Store session-only cookie (expires=None)
            cookies["user_email"] = idinfo["email"]
            cookies.save()
            st.rerun()
        except Exception as e:
            st.error(f"Google Login failed: {e}")
    st.stop()

# === Authenticated View ===
st.set_page_config(page_title="Chatbot", page_icon="🤖")
st.title("🤖 Chatbot")

col1, col2, col3 = st.columns([1, 1.5, 1])
with col2:
    if st.button("\u2795 Start New Chat"):
        st.session_state.messages = []
        st.session_state.current_chat_id = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        st.session_state.is_new_chat = True
        st.session_state.edit_index = -1
        st.rerun()

st.sidebar.success(f"Logged in as {st.session_state.user_email}")
if st.sidebar.button("Logout"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    cookies["user_email"] = ""
    cookies.save()
    st.rerun()

# === Sidebar Options ===
with st.sidebar:
    st.markdown("### ⚙️ Options")
    st.session_state.edit_mode = st.checkbox("✏️ Enable Edit Mode", value=st.session_state.edit_mode)
    st.markdown("### 🕒 Chats")
    st.cache_data.clear()
    st.session_state.chat_history = load_chats(st.session_state.user_email)
    for i, chat in reversed(list(enumerate(st.session_state.chat_history))):
        col1, col2 = st.columns([0.8, 0.2])
        with col1:
            if st.button(truncate_title(chat["title"]), key=f"load_chat_{i}"):
                st.session_state.messages = chat["messages"]
                st.session_state.current_chat_id = chat["chat_id"]
                st.session_state.is_new_chat = False
                st.session_state.edit_index = -1
                st.rerun()
        with col2:
            if st.button("🗑️", key=f"del_chat_{i}"):
                delete_chat(chat["chat_id"])
                st.cache_data.clear()
                # If deleting the current chat, clear session state for main panel
                if chat["chat_id"] == st.session_state.current_chat_id:
                    st.session_state.messages = []
                    st.session_state.current_chat_id = ""
                    st.session_state.is_new_chat = True
                    st.session_state.edit_index = -1
                st.rerun()

# === Display Messages ===
for i, msg in enumerate(st.session_state.messages):
    if msg["role"] == "user":
        if st.session_state.edit_mode and st.session_state.edit_index == i:
            new_input = st.text_input("Edit your message:", value=msg["content"], key=f"edit_input_{i}")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Save", key=f"save_edit_{i}"):
                    st.session_state.messages[i]["content"] = new_input
                    st.session_state.messages = st.session_state.messages[:i + 1]
                    st.session_state.edit_index = -1

                    full_response = ""
                    try:
                        stream = client.chat.completions.create(
                            model="llama3-8b-8192",
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
                        st.error(str(e))
                        full_response = f"❌ Error: {e}"

                    st.session_state.messages.append({"role": "assistant", "content": full_response})
                    save_chat()
                    st.rerun()
            with col2:
                if st.button("❌ Cancel", key=f"cancel_edit_{i}"):
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
if prompt := st.chat_input("Type your question..."):
    st.chat_message("user").markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    full_response = ""
    try:
        stream = client.chat.completions.create(
            model="llama3-8b-8192",
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
        st.error(str(e))
        full_response = f"❌ Error: {e}"

    st.session_state.messages.append({"role": "assistant", "content": full_response})
    save_chat()
    st.session_state.is_new_chat = False
    st.rerun()