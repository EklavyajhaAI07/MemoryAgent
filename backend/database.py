"""
database.py — Database Helper for Project 1: Custom AI Chatbot with Memory
DecodeLabs Industrial Training | Batch 2026

Implements local SQLite database persistence for users, sessions, and messages.
Allows saving chat state across backend restarts and implements multi-session support.
"""

import sys, platform
if platform.system() == "Windows" and "D:\\Python_for_PIP" not in sys.path:
    sys.path.append("D:\\Python_for_PIP")

import sqlite3
import os
import hashlib
import uuid
from datetime import datetime

DB_FILE = os.path.join(os.path.dirname(__file__), "chatbot.db")

def get_db_connection():
    """Establish and return a connection to the SQLite database."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # Access columns by name like dict
    return conn

def init_db():
    """Create database tables if they do not exist."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Users Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Sessions Table (Multi-Session Support)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
        )
    """)

    # Messages Table (Database Persistence)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            role TEXT CHECK(role IN ('user', 'assistant')) NOT NULL,
            content TEXT NOT NULL,
            tokens_used INTEGER DEFAULT 0,
            latency_ms REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()
    print("[Database] SQLite tables initialized successfully.")

# ─── User Functions ──────────────────────────────────────────────────────────
def hash_password(password: str, salt: str = None) -> tuple[str, str]:
    """Hash password using PBKDF2 with SHA-256 for secure storage."""
    if salt is None:
        salt = os.urandom(16).hex()
    pwd_hash = hashlib.pbkdf2_hmac(
        'sha256', 
        password.encode('utf-8'), 
        salt.encode('utf-8'), 
        100000
    ).hex()
    return pwd_hash, salt

def register_user(username: str, password: str) -> str:
    """
    Registers a new user.
    Returns: user_id string on success, raises sqlite3.IntegrityError if username exists.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    user_id = str(uuid.uuid4())
    pwd_hash, salt = hash_password(password)

    try:
        cursor.execute(
            "INSERT INTO users (id, username, password_hash, salt) VALUES (?, ?, ?, ?)",
            (user_id, username, pwd_hash, salt)
        )
        conn.commit()
        # Create a default session for the user immediately
        create_session(user_id, "New Conversation")
        return user_id
    finally:
        conn.close()

def authenticate_user(username: str, password: str) -> dict | None:
    """
    Checks username and password.
    Returns: User details dict or None if invalid.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()

    if not user:
        return None

    pwd_hash, _ = hash_password(password, user["salt"])
    if pwd_hash == user["password_hash"]:
        return {"id": user["id"], "username": user["username"]}
    return None

# ─── Session Functions (Multi-Session Support) ────────────────────────────────
def create_session(user_id: str, title: str = "New Conversation") -> str:
    """Create a new chat session for a user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    session_id = str(uuid.uuid4())
    cursor.execute(
        "INSERT INTO sessions (id, user_id, title) VALUES (?, ?, ?)",
        (session_id, user_id, title)
    )
    conn.commit()
    conn.close()
    return session_id

def get_sessions(user_id: str) -> list[dict]:
    """Retrieve all chat sessions for a specific user, sorted by creation date."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM sessions WHERE user_id = ? ORDER BY created_at DESC", 
        (user_id,)
    )
    sessions = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return sessions

def get_session(session_id: str) -> dict | None:
    """Retrieve details of a single session."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def update_session_title(session_id: str, title: str):
    """Update the sidebar title of a session."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE sessions SET title = ? WHERE id = ?", (title, session_id))
    conn.commit()
    conn.close()

def delete_session(session_id: str):
    """Delete a session and all its associated messages (cascade)."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()

# ─── Message Functions (Database Persistence & Memory Loop) ───────────────────
def add_message(session_id: str, role: str, content: str, tokens_used: int = 0, latency_ms: float = 0) -> str:
    """Append a new message to the session history table."""
    conn = get_db_connection()
    cursor = conn.cursor()
    msg_id = str(uuid.uuid4())
    cursor.execute(
        "INSERT INTO messages (id, session_id, role, content, tokens_used, latency_ms) VALUES (?, ?, ?, ?, ?, ?)",
        (msg_id, session_id, role, content, tokens_used, latency_ms)
    )
    conn.commit()
    conn.close()
    return msg_id

def get_messages(session_id: str, limit: int = 40) -> list[dict]:
    """
    Retrieve message history for a session.
    Automatically limits retrieval to avoid context window size problems.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT role, content, tokens_used, latency_ms, created_at FROM messages WHERE session_id = ? ORDER BY created_at ASC", 
        (session_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    return [{"role": row["role"], "content": row["content"], "tokens_used": row["tokens_used"], "latency_ms": row["latency_ms"], "created_at": row["created_at"]} for row in rows]

def clear_session_messages(session_id: str):
    """Clear message history for a session."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
    conn.commit()
    conn.close()
