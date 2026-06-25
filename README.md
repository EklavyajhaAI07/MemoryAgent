# 🤖 Project 1: Custom AI Chatbot with Memory

> **DecodeLabs Industrial Training | Batch 2026**

A stateful conversational AI chatbot powered by **Groq (Llama-3.3-70b-versatile)** with an automatic fallback to **Claude Sonnet (claude-sonnet-4-6)** via the Anthropic SDK. Implements the artificial memory loop: `Input (Mₜ) + History (Hₜ₋₁) → LLM API → Response (Rₜ) → Append to History`.

---

## 🏗 Architecture

```
project1-chatbot/
├── backend/
│   ├── app.py              # Flask REST API (POST /chat, POST /clear, GET /history, GET /health)
│   ├── chat.py             # Core memory loop — sliding window FIFO, Hindsight logging
│   ├── requirements.txt
│   └── .env.example        # Copy to .env and fill in your API keys
├── frontend/
│   ├── src/
│   │   ├── ChatApp.jsx     # Premium React chat UI
│   │   ├── index.css       # Dark-mode design system
│   │   └── main.jsx        # React entry point
│   ├── index.html
│   ├── vite.config.js      # Dev proxy → backend on :5000
│   └── package.json
└── tests/
    └── test_memory.py      # 3-step memory audit test
```

---

## ⚡ Quick Start

### 1. Clone & configure environment

```bash
cd backend
cp .env.example .env
# Edit .env — fill in GROQ_API_KEY, ANTHROPIC_API_KEY, and HINDSIGHT_API_KEY
```

### 2. Install Python dependencies & start backend

```bash
cd backend
pip install -r requirements.txt
python app.py
# Flask running at http://localhost:5000
```

### 3. Install Node dependencies & start frontend

```bash
cd frontend
npm install
npm run dev
# React app running at http://localhost:3000
```

### 4. Run the memory audit test

```bash
# In a third terminal (while backend is running)
python tests/test_memory.py
```

---

## 🔌 API Endpoints

| Method | Route      | Description                              |
|--------|------------|------------------------------------------|
| POST   | `/chat`    | Send a message, get AI reply + metadata  |
| POST   | `/clear`   | Reset conversation session               |
| GET    | `/history` | View current conversation history array  |
| GET    | `/health`  | Server health + session stats            |

**POST /chat request body:**
```json
{ "message": "Hello, my name is Vipin" }
```

**POST /chat response:**
```json
{
  "reply": "Hello Vipin! Nice to meet you...",
  "tokens_used": 142,
  "latency_ms": 823.5,
  "history_length": 2
}
```

---

## 🧠 Memory Loop

The core mechanic (implemented in `chat.py`):

1. **Validate** — reject empty/whitespace input before appending
2. **Append** — add user message to `conversation_history[]`
3. **Prune** — sliding window FIFO (prune oldest *pairs* when > `MAX_HISTORY_TURNS`)
4. **Call API** — send full history as `messages` payload every turn
5. **Extract** — get response text and token counts (handles both Groq and Anthropic)
6. **Append** — add assistant reply to history
7. **Log** — non-blocking Hindsight observability trace

---

## 🧪 Memory Audit (3-Step Test)

| Step | Action | Purpose |
|------|--------|---------|
| 1 | `"My name is Vipin"` | State initialization |
| 2 | `"Write a poem about AI"` | Context distraction (large token generation) |
| 3 | `"What is my name?"` | State extraction — must recall "Vipin" |

---

## 🔍 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | ✅ Yes (pref) | Groq API Key (gsk_...) - Runs Llama-3.3-70b-versatile (highly recommended) |
| `ANTHROPIC_API_KEY` | Optional | Fallback Anthropic API key (console.anthropic.com) |
| `HINDSIGHT_API_KEY` | Optional | Hindsight observability key (skipped if empty) |

---

*DecodeLabs | Batch 2026 | Project 1*
