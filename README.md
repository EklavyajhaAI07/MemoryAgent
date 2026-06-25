# ⚡ MemoryAgent — Stateful AI Chatbot with Memory

<p align="center">
  <img src="/public/Logo-Favicon.png" alt="MemoryAgent Logo" width="120"/>
</p>

<p align="center">
  <strong>A production-aware conversational AI chatbot with persistent in-session memory, sliding window context management, and built-in observability.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python" />
  <img src="https://img.shields.io/badge/Flask-3.0+-black?style=flat-square&logo=flask" />
  <img src="https://img.shields.io/badge/React-18+-61DAFB?style=flat-square&logo=react" />
  <img src="https://img.shields.io/badge/Claude-Sonnet%204.6-purple?style=flat-square" />
  <img src="https://img.shields.io/badge/Groq-Llama%203-orange?style=flat-square" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=flat-square" />
</p>

---

## 📖 Table of Contents

- [Overview](#-overview)
- [System Architecture](#-system-architecture)
- [Data Flow](#-data-flow)
- [Tech Stack](#-tech-stack)
- [The Memory Loop](#-the-memory-loop-core-concept)
- [Features](#-features)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
- [API Reference](#-api-reference)
- [Memory Audit Test](#-memory-audit-test)
- [Known Pitfalls & Fixes](#-known-pitfalls--fixes)
- [Observability](#-observability--hindsight)

---

## 🧠 Overview

**MemoryAgent** is a stateful conversational AI system that solves a fundamental problem with LLMs: *they are stateless by default*. Every request to an LLM API is independent — it has no idea what you said 2 messages ago unless you explicitly pass that history.

MemoryAgent builds the **artificial memory layer** on top of the API, maintaining a running conversation history array that gets sent with every request. This creates the illusion of a "remembering" AI.

> **Core mechanic:** `Input (Mₜ) + History (Hₜ₋₁) → LLM API → Response (Rₜ) → Append to History (Hₜ)`

This project is built for **DecodeLabs Industrial Training — Batch 2026** as Project 1.

---

## 🏗 System Architecture

The system is divided into 3 layers — User, Frontend, and Backend — each with distinct responsibilities:

![MemoryAgent System Architecture](/public/SystemArchitecture.png)

| Layer | Component | Responsibility |
|-------|-----------|----------------|
| **User Layer** | Browser | Sends requests with JWT access tokens |
| **Frontend Layer** | React + Vite | UI components, state management, Axios API client |
| **Backend Layer** | Python Flask | MemoryAgent logic, session state, LLM API calls |
| **Database** | SQLite (dev) / PostgreSQL (prod) | Persist conversations, agent state, memories, metadata |
| **LLM API** | Groq / Claude | Generates completions from the full history payload |

The **Stateful Memory Loop** at the heart of the system follows this cycle continuously:

```
Store → Retrieve → Reason → Respond → Store
```

---

## 🔄 Data Flow

Every message travels through 7 steps before a response is returned:

![MemoryAgent Data Flow](/public/Dataflow.png)

1. **User Input** — Raw text message from the browser
2. **Validation Gate** — Sanitize input, check limits, classify intent, rate-limit
3. **Conversation History Array** — The in-memory array holding all prior turns
4. **LLM API (Groq / Claude)** — Receives full history, generates completion
5. **Response** — Assistant reply extracted from API response
6. **Sliding Window (Prune)** — Keep only the last N messages; drop oldest outside the window
7. **Hindsight Logger (Async)** — Non-blocking observability: log interaction, store metadata, analytics

> The Hindsight Logger runs as a **non-blocking branch** — it never delays the user's response.

---

## 🛠 Tech Stack

![Tech Stack Diagram](/public/Screenshot_2026-06-25_100944.png)

| Layer | Choice | Notes |
|-------|--------|-------|
| **Language** | Python 3.10+ | Primary backend language |
| **Backend** | Flask / FastAPI | REST API server |
| **Frontend** | React (Vite) | Chat bubble UI, typing indicator |
| **LLM SDK** | Anthropic `claude-sonnet-4-6` / Groq Llama 3 | Frontier model via official SDK |
| **Auth** | JWT (Access Tokens) | Passed Browser → Frontend → Backend |
| **Database** | SQLite (dev) → PostgreSQL (prod) | Session persistence |
| **Observability** | Hindsight (`HINDSIGHT_API_KEY`) | Log every turn, token usage, latency |

---

## 🔁 The Memory Loop (Core Concept)

![Backend Architecture](/public/Screenshot_2026-06-25_100737.png)

This is the most important concept in the entire project. Understand this and everything else follows naturally.

```python
conversation_history: list[dict] = []

# The history array looks like this after 2 turns:
# [
#   {"role": "user",      "content": "My name is Vipin"},
#   {"role": "assistant", "content": "Nice to meet you, Vipin!"},
#   {"role": "user",      "content": "What is my name?"},
#   {"role": "assistant", "content": "Your name is Vipin."}
# ]
```

### The `chat()` Function — Step by Step

```python
def chat(user_input: str) -> str:
    # STEP 1: Validation Gate — block empty/whitespace input
    if not user_input or not user_input.strip():
        return "[Error] Empty input. Please type a message."

    # STEP 2: Append user message to history
    conversation_history.append({"role": "user", "content": user_input.strip()})

    # STEP 3: Sliding window — prune oldest pairs if over limit
    # Always remove in pairs (user + assistant) to maintain role alternation
    while len(conversation_history) > MAX_HISTORY_TURNS * 2:
        conversation_history.pop(0)
        if conversation_history and conversation_history[0]["role"] == "assistant":
            conversation_history.pop(0)

    # STEP 4: Call LLM API with full history as payload
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=conversation_history   # <-- entire history sent every turn
    )

    # STEP 5: Extract and append response
    reply = response.content[0].text
    conversation_history.append({"role": "assistant", "content": reply})

    return reply
```

---

## ✨ Features

| Feature | Description | Status |
|---------|-------------|--------|
| 🧠 **In-Memory History** | Maintains full conversation array per session | ✅ |
| 🔒 **Input Validation Gate** | Blocks empty/whitespace before hitting the API | ✅ |
| 🪟 **Sliding Window (FIFO)** | Prunes oldest message pairs to prevent token overflow | ✅ |
| 💬 **System Prompt** | Configurable persona/instructions sent with every request | ✅ |
| 🔄 **Session Clear** | `/clear` endpoint wipes history, resets session | ✅ |
| 📊 **Token Counter** | Track usage per turn via API response metadata | ✅ |
| 🔭 **Hindsight Observability** | Async logging of every turn — non-blocking | ✅ |
| ⚡ **Streaming Output** | Real-time token stream to frontend | 🔜 |
| 🗄 **PostgreSQL Persistence** | Persist sessions beyond server restarts (prod) | 🔜 |
| 🔐 **JWT Auth** | Secure browser ↔ frontend ↔ backend communication | ✅ |

---

## 📁 Project Structure

```
project1-chatbot/
├── backend/
│   ├── app.py              # Flask server + route definitions
│   ├── chat.py             # Core memory loop logic
│   ├── requirements.txt    # Python dependencies
│   └── .env                # API keys (never commit!)
├── frontend/
│   ├── src/
│   │   └── ChatApp.jsx     # React chat UI component
│   └── package.json
└── tests/
    └── test_memory.py      # 3-step memory audit test
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- An Anthropic or Groq API key

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/memoryagent.git
cd memoryagent
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env and add your keys
```

### 3. Configure `.env`

```env
ANTHROPIC_API_KEY=your_anthropic_key_here
HINDSIGHT_API_KEY=your_hindsight_key_here
```

> ⚠️ **Never commit `.env` to version control.** It's already in `.gitignore`.

### 4. Run the Backend

```bash
python app.py
# Server starts at http://localhost:5000
```

### 5. Frontend Setup

```bash
cd frontend
npm install
npm run dev
# Frontend starts at http://localhost:5173
```

---

## 📡 API Reference

### `POST /chat`

Send a user message and receive an AI reply.

**Request Body:**
```json
{
  "message": "What is my name?"
}
```

**Response:**
```json
{
  "reply": "Your name is Vipin."
}
```

---

### `POST /clear`

Reset the session — wipes entire conversation history.

**Response:**
```json
{
  "status": "[Session cleared. Starting fresh.]"
}
```

---

### `GET /health`

Check server status and current history length.

**Response:**
```json
{
  "status": "ok",
  "history_length": 6
}
```

---

## 🧪 Memory Audit Test

Run this 3-step test to verify that memory is working correctly after starting your server:

```python
# tests/test_memory.py
import requests

BASE = "http://localhost:5000"

# Step 1: State initialization — plant a fact
r1 = requests.post(f"{BASE}/chat", json={"message": "My name is Vipin"})
print("Turn 1:", r1.json()["reply"])

# Step 2: Context distraction — force large token processing
r2 = requests.post(f"{BASE}/chat", json={"message": "Write a poem about AI and the future of tech"})
print("Turn 2:", r2.json()["reply"][:100], "...")

# Step 3: State extraction — must recall "Vipin" despite distraction
r3 = requests.post(f"{BASE}/chat", json={"message": "What is my name?"})
print("Turn 3:", r3.json()["reply"])

assert "Vipin" in r3.json()["reply"], "❌ MEMORY FAILED — name not retained"
print("✅ Memory test passed")
```

**Expected output:**
```
Turn 1: Nice to meet you, Vipin! How can I help you today?
Turn 2: In circuits bright and data streams that flow...
Turn 3: Your name is Vipin.
✅ Memory test passed
```

---

## ⚠️ Known Pitfalls & Fixes

| Pitfall | Cause | Fix |
|---------|-------|-----|
| `400 Bad Request` from API | Empty string sent in messages array | Validation gate before appending to history |
| Context window overflow | History grows unbounded over long sessions | Sliding window FIFO — prune oldest pairs |
| `role` alternation error | Two consecutive same-role messages | Always: append user → call API → append assistant |
| History lost on restart | RAM is ephemeral | Use PostgreSQL / Firestore in production |
| CORS error in browser | Flask missing CORS headers | Add `flask-cors`, call `CORS(app)` at startup |
| Hindsight logging crashes chat | Logging exception bubbles up | Wrap in `try/except` — log failures silently |

---

## 🔭 Observability — Hindsight

Every conversation turn is logged asynchronously to Hindsight for:

- **Token usage tracking** per turn
- **Latency monitoring** (ms per API call)
- **History length** at time of each call
- **Debugging** memory failures and context gaps

```python
def log_to_hindsight(user_input, response_text, tokens_used, latency_ms):
    """Non-blocking observability logger — wraps every LLM call."""
    try:
        requests.post(
            "https://api.hindsight.dev/v1/log",
            headers={"Authorization": f"Bearer {HINDSIGHT_API_KEY}"},
            json={
                "input": user_input,
                "output": response_text,
                "tokens": tokens_used,
                "latency_ms": latency_ms,
                "metadata": {
                    "history_length": len(conversation_history),
                    "model": "claude-sonnet-4-6"
                }
            },
            timeout=3
        )
    except Exception as e:
        print(f"[Hindsight] Logging failed silently: {e}")
        # Never let logging crash the chat response
```

> Check [Hindsight's official docs](https://hindsight.dev) for the exact endpoint and payload schema.

---

## 📦 Requirements

```
anthropic>=0.25.0
flask>=3.0.0
flask-cors>=4.0.0
python-dotenv>=1.0.0
requests>=2.31.0
```

---

## 🏫 About

Built as part of **DecodeLabs Industrial Training — Batch 2026**

> Project 1: Custom AI Chatbot with Memory

This project is designed as a **learning artifact** — every section of the memory loop is commented, every decision is justified, and the architecture is intentionally kept readable over clever.

---

<p align="center">
  Made with 🧠 + ⚡ by DecodeLabs Batch 2026
</p>
