"""
test_memory.py — Stateful Memory Audit for Secured Groq Chatbot
DecodeLabs Industrial Training | Batch 2026

Runs a 3-step memory audit against the JWT-secured Flask API using the Groq backend.

Steps:
  1. Register & Login test user to get a JWT token.
  2. Create a new session.
  3. Send User Prompt 1: "My name is Vipin" (State initialization)
  4. Send User Prompt 2: "Write a poem about AI" (Context distraction)
  5. Send User Prompt 3: "What is my name?" (State extraction — must recall "Vipin")
  6. Clean up: Delete session.
"""

import requests
import sys
import random

BASE = "http://localhost:5000/api"

def separator(title: str) -> None:
    print(f"\n{'-' * 50}")
    print(f"  {title}")
    print(f"{'-' * 50}")

def run_secured_memory_audit() -> None:
    # Generate unique credentials for the test run
    test_username = f"testuser_{random.randint(1000, 9999)}"
    test_password = "password123"

    separator("SETUP - Authentication & Session Creation")

    # 1. Register
    reg_url = f"{BASE}/register"
    reg_resp = requests.post(reg_url, json={"username": test_username, "password": test_password}, timeout=10)
    reg_resp.raise_for_status()
    print(f"Registered test user: {test_username}")

    # 2. Login to get JWT Token
    login_url = f"{BASE}/login"
    login_resp = requests.post(login_url, json={"username": test_username, "password": test_password}, timeout=10)
    login_resp.raise_for_status()
    token = login_resp.json()["token"]
    print("JWT Token acquired successfully.")

    # Headers for secured endpoints
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # 3. Create a Session
    sess_url = f"{BASE}/sessions"
    sess_resp = requests.post(sess_url, json={"title": "Memory Test Session"}, headers=headers, timeout=10)
    sess_resp.raise_for_status()
    session_id = sess_resp.json()["session_id"]
    print(f"Created chat session. Session ID: {session_id}")

    # ─── Begin Memory Audit ───

    # Step 1: State Initialization
    separator("STEP 1 - State Initialization")
    r1 = requests.post(
        f"{BASE}/chat", 
        json={"message": "My name is Vipin", "session_id": session_id}, 
        headers=headers,
        timeout=30
    )
    r1.raise_for_status()
    reply1 = r1.json()["reply"]
    print(f"User   : My name is Vipin")
    print(f"Bot    : {reply1}")
    print(f"Tokens : {r1.json().get('tokens_used', 'N/A')} | Latency: {r1.json().get('latency_ms', 'N/A')} ms")

    # Step 2: Context Distraction
    separator("STEP 2 - Context Distraction (Large Token Processing)")
    r2 = requests.post(
        f"{BASE}/chat",
        json={"message": "Write a short poem about artificial intelligence and the future of tech", "session_id": session_id},
        headers=headers,
        timeout=60
    )
    r2.raise_for_status()
    reply2 = r2.json()["reply"]
    print(f"User   : Write a poem about AI and the future of tech")
    print(f"Bot    : {reply2[:120]}...")
    print(f"Tokens : {r2.json().get('tokens_used', 'N/A')} | Latency: {r2.json().get('latency_ms', 'N/A')} ms")

    # Step 3: State Extraction
    separator("STEP 3 - State Extraction (Memory Recall Check)")
    r3 = requests.post(
        f"{BASE}/chat", 
        json={"message": "What is my name?", "session_id": session_id}, 
        headers=headers,
        timeout=30
    )
    r3.raise_for_status()
    reply3 = r3.json()["reply"]
    print(f"User   : What is my name?")
    print(f"Bot    : {reply3}")
    print(f"Tokens : {r3.json().get('tokens_used', 'N/A')} | Latency: {r3.json().get('latency_ms', 'N/A')} ms")

    # Audit validation check
    separator("MEMORY AUDIT RESULT")
    if "Vipin" in reply3:
        print("[SUCCESS] Secured memory test PASSED - name retained across turns using Groq!")
    else:
        print("[ERROR] SECURED MEMORY FAILED - name not found in reply.")
        print(f"   Expected 'Vipin' in reply, got: {reply3}")
        sys.exit(1)

    # Cleanup Session
    separator("CLEANUP - Deleting Session")
    del_url = f"{BASE}/sessions/{session_id}"
    del_resp = requests.delete(del_url, headers=headers, timeout=10)
    print(f"Cleanup response: {del_resp.json()['status']}")
    print("\n[SUCCESS] Secured audit completed successfully.\n")

if __name__ == "__main__":
    try:
        run_secured_memory_audit()
    except requests.exceptions.ConnectionError:
        print("\n[ERROR]: Could not connect to the Flask server.")
        print("   Make sure the backend is running: cd backend && python app.py\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {str(e)}\n")
        sys.exit(1)
