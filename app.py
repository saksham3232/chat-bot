import streamlit as st
from groq import Groq
from dotenv import load_dotenv
import os

# Load environment variables from .env
load_dotenv()
# Load API key from Streamlit secrets or .env
# GROQ_API_KEY = st.secrets.get("GROQ_API_KEY") or os.getenv("GROQ_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Initialize Groq client
client = Groq(api_key=GROQ_API_KEY)

# Set Streamlit page config
st.set_page_config(page_title="Groq Chatbot", page_icon="🤖")
st.title("🤖 Groq Chatbot")
st.divider()

# Initialize session state
if "groq_model" not in st.session_state:
    st.session_state["groq_model"] = "llama3-8b-8192"  # You can also use llama3-70b-8192, mixtral-8x7b-32768

if "messages" not in st.session_state:
    st.session_state["messages"] = []

# Display past messages
for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Handle user prompt
if prompt := st.chat_input("Say something..."):
    # Display user's message
    st.chat_message("user").markdown(prompt)
    st.session_state["messages"].append({"role": "user", "content": prompt})

    # Assistant response block
    with st.chat_message("assistant"):
        full_response = ""
        response_placeholder = st.empty()

        with st.spinner("Thinking... 🤖"):
            try:
                # Request streaming response from Groq
                stream = client.chat.completions.create(
                    model=st.session_state["groq_model"],
                    messages=st.session_state["messages"],
                    stream=True,
                )

                # Stream response as it arrives
                for chunk in stream:
                    delta = chunk.choices[0].delta
                    if delta and delta.content:
                        full_response += delta.content
                        response_placeholder.markdown(full_response)

            except Exception as e:
                full_response = f"❌ Error: {e}"
                response_placeholder.error(full_response)

        # Save assistant message
        st.session_state["messages"].append({"role": "assistant", "content": full_response})
