"""
chat.py — Core Memory Loop (Groq Exclusive with DB Persistence & Streaming)
DecodeLabs Industrial Training | Batch 2026

Implements the memory loop:
  Input (Mₜ) + History (Hₜ₋₁) → Groq LLM API → Response (Rₜ) → Database Log

Features:
  - SQLite Database integration for multi-session and multi-user persistence
  - Prunes context using a sliding window directly from the DB messages
  - Streaming generation support via Generator function yielding SSE chunks
  - Automatic session naming based on the first prompt
"""

import sys, platform
if platform.system() == "Windows" and "D:\\Python_for_PIP" not in sys.path:
    sys.path.append("D:\\Python_for_PIP")

import os
import time
import json
import requests
from dotenv import load_dotenv
import groq
from database import init_db, get_messages, add_message, update_session_title

# ─── Initialization ───────────────────────────────────────────────────────────
load_dotenv()
init_db()  # Initialize the local SQLite tables on startup

GROQ_KEY = os.environ.get("GROQ_API_KEY")
if not GROQ_KEY:
    raise ValueError("[Error] GROQ_API_KEY is not defined in your .env file.")

# Groq Client Initialization (Anthropic support completely removed)
client = groq.Groq(api_key=GROQ_KEY)
MODEL_NAME = "llama-3.3-70b-versatile"
MAX_TOKENS = 1024
MAX_HISTORY_TURNS = 20  # Keep last 20 turns (40 messages total) in context payload

SYSTEM_PROMPT = (
    "You are a helpful AI assistant with a friendly, concise tone. "
    "Remember everything the user tells you during this session. "
    "If asked about information shared earlier in the conversation, recall it accurately."
)

# ─── Hindsight Observability ──────────────────────────────────────────────────
HINDSIGHT_ENDPOINT = "https://app.usehindsight.com/api/v1/responses"

def log_to_hindsight(user_input: str, response_text: str, tokens_used: int, latency_ms: float, session_id: str) -> None:
    """Log conversation turn to Hindsight for tracing (wrapped to never crash main loop)."""
    hindsight_key = os.environ.get("HINDSIGHT_API_KEY", "")
    if not hindsight_key:
        return
    try:
        payload = {
            "messages": [
                {"role": "user",      "content": user_input},
                {"role": "assistant", "content": response_text},
            ],
            "stream": False,
            "metadata": {
                "model": MODEL_NAME,
                "tokens_used": tokens_used,
                "latency_ms": round(latency_ms, 2),
                "project": "DecodeLabs-Project1-GroqChatbot",
                "session_id": session_id,
            }
        }
        requests.post(
            HINDSIGHT_ENDPOINT,
            headers={
                "Authorization": f"Bearer {hindsight_key}",
                "Content-Type":  "application/json",
            },
            json=payload,
            timeout=3
        )
    except Exception as e:
        print(f"[Hindsight] Logging failed silently: {e}")

# ─── Core Memory Loop (Static Response) ───────────────────────────────────────
def chat(session_id: str, user_input: str) -> dict:
    """
    Standard chat loop using Groq. Saves user prompt and assistant response to SQLite.
    Automatically sliding-windows context to avoid token/alternation issues.
    """
    if not user_input or not user_input.strip():
        return {"reply": None, "error": "Empty input."}

    sanitized_input = user_input.strip()

    # 1. Fetch existing message history from database
    db_history = get_messages(session_id)
    
    # Auto-rename session title if this is the user's first message in it
    if len(db_history) == 0:
        short_title = sanitized_input[:28] + "..." if len(sanitized_input) > 28 else sanitized_input
        update_session_title(session_id, short_title)

    # 2. Append User Message to DB
    add_message(session_id, "user", sanitized_input)

    # 3. Create sliding window for API context payload (last MAX_HISTORY_TURNS pairs)
    messages_payload = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # We slice to ensure we only send a maximum of MAX_HISTORY_TURNS pairs (FIFO pruning)
    max_history_entries = MAX_HISTORY_TURNS * 2
    pruned_history = db_history[-max_history_entries:] if len(db_history) > max_history_entries else db_history
    
    # Build payload for Groq
    for msg in pruned_history:
        messages_payload.append({"role": msg["role"], "content": msg["content"]})
        
    # Add current user prompt
    messages_payload.append({"role": "user", "content": sanitized_input})

    # 4. Call Groq LLM API
    latency_start = time.time()
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages_payload,
        max_tokens=MAX_TOKENS,
    )
    latency_ms = (time.time() - latency_start) * 1000

    # 5. Extract Reply and Metadata
    reply = response.choices[0].message.content
    tokens_used = response.usage.total_tokens

    # 6. Save assistant response to DB
    add_message(session_id, "assistant", reply, tokens_used, latency_ms)

    # 7. Observability Logging (non-blocking)
    log_to_hindsight(sanitized_input, reply, tokens_used, latency_ms, session_id)

    return {
        "reply": reply,
        "tokens_used": tokens_used,
        "latency_ms": round(latency_ms, 2),
        "error": None
    }

# ─── Core Memory Loop (Streaming Response) ────────────────────────────────────
def chat_stream(session_id: str, user_input: str):
    """
    Generator for Server-Sent Events (SSE) streaming with Groq.
    Updates the database with the full assistant response once generation is complete.
    """
    if not user_input or not user_input.strip():
        yield "data: {\"error\": \"Empty input\"}\n\n"
        return

    sanitized_input = user_input.strip()

    # 1. Fetch message history
    db_history = get_messages(session_id)
    
    # Auto-rename session
    if len(db_history) == 0:
        short_title = sanitized_input[:28] + "..." if len(sanitized_input) > 28 else sanitized_input
        update_session_title(session_id, short_title)

    # 2. Add User Message to DB
    add_message(session_id, "user", sanitized_input)

    # 3. Create sliding window payload
    messages_payload = [{"role": "system", "content": SYSTEM_PROMPT}]
    max_history_entries = MAX_HISTORY_TURNS * 2
    pruned_history = db_history[-max_history_entries:] if len(db_history) > max_history_entries else db_history
    
    for msg in pruned_history:
        messages_payload.append({"role": msg["role"], "content": msg["content"]})
    messages_payload.append({"role": "user", "content": sanitized_input})

    # 4. Stream response from Groq
    latency_start = time.time()
    stream = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages_payload,
        max_tokens=MAX_TOKENS,
        stream=True
    )

    full_reply = ""
    # Stream chunks back to client
    for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta:
            full_reply += delta
            # Format according to EventStream standard
            yield f"data: {json.dumps({'chunk': delta})}\n\n"

    latency_ms = (time.time() - latency_start) * 1000
    
    # Roughly calculate token count (4 chars ≈ 1 token) for analytics
    estimated_tokens = (len(sanitized_input) + len(full_reply)) // 4

    # 5. Save final compiled response to database
    add_message(session_id, "assistant", full_reply, estimated_tokens, latency_ms)

    # 6. Observability
    log_to_hindsight(sanitized_input, full_reply, estimated_tokens, latency_ms, session_id)

    # Yield final confirmation chunk with complete metadata
    yield f"data: {{\"done\": true, \"tokens_used\": {estimated_tokens}, \"latency_ms\": {round(latency_ms)}}}\n\n"
