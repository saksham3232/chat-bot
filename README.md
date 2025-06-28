# 🤖 Groq Chatbot

A simple chatbot app built with [Streamlit](https://streamlit.io/) and powered by [Groq](https://groq.com/) large language models.
This chatbot uses **only the `llama3-8b-8192` model** for all conversations.

## Features

- 💬 Real-time chat with Groq Llama 3-8B model (`llama3-8b-8192`)
- 🧠 Remembers the conversation during your session
- 🚀 Fast, streaming responses
- 🔒 Secure configuration (API key via `.env` or Streamlit secrets)

## Getting Started

### Prerequisites

- Python 3.8+
- Groq API key ([Get one here](https://console.groq.com/))
- [Streamlit](https://streamlit.io/) for running locally

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/saksham3232/chat-bot.git
   cd chat-bot
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up your API key:**
   - Create a `.env` file in the project root:
     ```
     GROQ_API_KEY=your_groq_api_key_here
     ```
   - Or use Streamlit secrets if deploying on Streamlit Cloud.

### Running the Chatbot

```bash
streamlit run app.py
```
Open your browser to the URL Streamlit provides (usually [http://localhost:8501](http://localhost:8501)).

## Usage

- Type your message in the chat box and press Enter.
- All responses use the `llama3-8b-8192` model.
- Conversation history is preserved during your session.

## Project Structure

```
.
├── app.py            # Streamlit app
├── requirements.txt  # Python dependencies
└── README.md         # Project info
```



---

*This project is for demonstration/educational purposes. Powered by [Groq](https://groq.com/) and [Streamlit](https://streamlit.io/).*
