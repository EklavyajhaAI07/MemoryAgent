"""
app.py — Flask API Server with JWT Auth, Multi-Session, and Response Streaming
DecodeLabs Industrial Training | Batch 2026

Endpoints:
  POST /api/register        — Sign up a new user
  POST /api/login           — Log in and get JWT token
  GET  /api/sessions        — Get all sessions for active user
  POST /api/sessions        — Create a new chat session
  GET  /api/sessions/<id>   — Get message history of a session
  DELETE /api/sessions/<id> — Delete a session
  POST /api/chat            — Standard chat generation
  POST /api/chat/stream     — Server-Sent Events (SSE) streaming chat generation
  GET  /api/health          — Backend status
"""

import sys, platform
if platform.system() == "Windows" and "D:\\Python_for_PIP" not in sys.path:
    sys.path.append("D:\\Python_for_PIP")

import os
from functools import wraps
from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
import jwt
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Database and Chat logic imports
from database import (
    register_user, authenticate_user, get_sessions, 
    create_session, get_session, delete_session, get_messages
)
from chat import chat, chat_stream

# ─── Initialization ───────────────────────────────────────────────────────────
load_dotenv()
app = Flask(__name__)

# In production, restrict CORS to the deployed frontend URL only.
# Set FRONTEND_URL in your Render environment variables dashboard.
# Falls back to allowing all origins for local development.
FRONTEND_URL = os.environ.get("FRONTEND_URL", "*")
CORS(app, origins=FRONTEND_URL)

# JWT Secret config — use a strong secret in production via environment variables
JWT_SECRET = os.environ.get("JWT_SECRET", "decodelabs_secret_key_2026")

# ─── Auth Decorator ───────────────────────────────────────────────────────────
def token_required(f):
    """Decorator to require valid JWT token in Authorization header."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        # Check Authorization header
        if "Authorization" in request.headers:
            auth_header = request.headers["Authorization"]
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]

        if not token:
            return jsonify({"error": "Authorization token is missing!"}), 401

        try:
            # Decode token payload
            data = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            current_user = {"id": data["user_id"], "username": data["username"]}
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired!"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token!"}), 401

        return f(current_user, *args, **kwargs)

    return decorated

# ─── Authentication Routes ───────────────────────────────────────────────────

@app.route("/api/register", methods=["POST"])
def handle_register():
    """Register a new user account."""
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        return jsonify({"error": "Username and password are required."}), 400

    try:
        user_id = register_user(username, password)
        return jsonify({
            "message": "User registered successfully.",
            "user_id": user_id
        }), 201
    except Exception as e:
        # Catch duplicate username constraint failures
        return jsonify({"error": "Username already exists."}), 409


@app.route("/api/login", methods=["POST"])
def handle_login():
    """Authenticate user and issue JWT token."""
    data = request.get_json(silent=True) or {}
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        return jsonify({"error": "Username and password are required."}), 400

    user = authenticate_user(username, password)
    if not user:
        return jsonify({"error": "Invalid username or password."}), 401

    # Issue JWT token expiring in 24 hours
    token = jwt.encode({
        "user_id": user["id"],
        "username": user["username"],
        "exp": datetime.utcnow() + timedelta(hours=24)
    }, JWT_SECRET, algorithm="HS256")

    return jsonify({
        "token": token,
        "user": user
    })

# ─── Session Management Routes ────────────────────────────────────────────────

@app.route("/api/sessions", methods=["GET"])
@token_required
def handle_get_sessions(current_user):
    """Retrieve all chat sessions for the logged-in user."""
    sessions = get_sessions(current_user["id"])
    return jsonify({"sessions": sessions})


@app.route("/api/sessions", methods=["POST"])
@token_required
def handle_create_session(current_user):
    """Create a new conversation session."""
    data = request.get_json(silent=True) or {}
    title = data.get("title", "New Conversation").strip()
    session_id = create_session(current_user["id"], title)
    return jsonify({
        "session_id": session_id,
        "title": title
    }), 201


@app.route("/api/sessions/<session_id>", methods=["GET"])
@token_required
def handle_get_session_messages(current_user, session_id):
    """Fetch complete message history for a specific session (verifies owner)."""
    session_details = get_session(session_id)
    if not session_details or session_details["user_id"] != current_user["id"]:
        return jsonify({"error": "Session not found or access denied."}), 404

    messages = get_messages(session_id)
    return jsonify({
        "session_id": session_id,
        "title": session_details["title"],
        "messages": messages
    })


@app.route("/api/sessions/<session_id>", methods=["DELETE"])
@token_required
def handle_delete_session(current_user, session_id):
    """Delete a session (verifies owner)."""
    session_details = get_session(session_id)
    if not session_details or session_details["user_id"] != current_user["id"]:
        return jsonify({"error": "Session not found or access denied."}), 404

    delete_session(session_id)
    return jsonify({"status": "Session deleted successfully."})

# ─── Conversational AI Chat Routes ────────────────────────────────────────────

@app.route("/api/chat", methods=["POST"])
@token_required
def handle_chat(current_user):
    """Standard (static) chat endpoint."""
    data = request.get_json(silent=True) or {}
    message = data.get("message", "").strip()
    session_id = data.get("session_id", "").strip()

    if not message or not session_id:
        return jsonify({"error": "message and session_id are required fields."}), 400

    # Safety check: ensure active user owns the targeted session
    session_details = get_session(session_id)
    if not session_details or session_details["user_id"] != current_user["id"]:
        return jsonify({"error": "Session not found or access denied."}), 404

    result = chat(session_id, message)
    if result.get("error"):
        return jsonify({"error": result["error"]}), 400

    return jsonify(result)


@app.route("/api/chat/stream", methods=["POST"])
@token_required
def handle_chat_stream(current_user):
    """Streaming chat endpoint using Server-Sent Events (SSE)."""
    data = request.get_json(silent=True) or {}
    message = data.get("message", "").strip()
    session_id = data.get("session_id", "").strip()

    if not message or not session_id:
        return jsonify({"error": "message and session_id are required fields."}), 400

    session_details = get_session(session_id)
    if not session_details or session_details["user_id"] != current_user["id"]:
        return jsonify({"error": "Session not found or access denied."}), 404

    # Stream chunks dynamically to the client using chunked encoding
    return Response(
        stream_with_context(chat_stream(session_id, message)),
        mimetype="text/event-stream"
    )

# ─── System Health check ──────────────────────────────────────────────────────

@app.route("/api/health", methods=["GET"])
def health():
    """Verify backend API health status."""
    return jsonify({
        "status": "ok",
        "database": "sqlite3",
        "llm_provider": "groq",
        "auth_model": "JWT"
    })

# ─── Server Entry ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # debug=False in production (Render sets the PORT env var)
    is_production = os.environ.get("PORT") is not None
    app.run(debug=not is_production, port=int(os.environ.get("PORT", 5000)), host="0.0.0.0")
