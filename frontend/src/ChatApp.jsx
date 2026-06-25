/**
 * ChatApp.jsx — MemoryAgent: Premium Chat UI with GSAP, Themes, & Canvas Cursor Physics
 * Stateful AI Chatbot | DecodeLabs Industrial Training | Batch 2026
 */

import { useState, useRef, useEffect, useCallback } from "react";
import { gsap } from "gsap";

const API_BASE = import.meta.env.VITE_API_BASE ?? "/api";

// ── GSAP animation helpers ────────────────────────────────────────────────────
const animateIn = (el, delay = 0) => {
  if (!el) return;
  gsap.fromTo(el,
    { opacity: 0, y: 20, scale: 0.97 },
    { opacity: 1, y: 0, scale: 1, duration: 0.4, delay, ease: "power3.out" }
  );
};

const animateSlideIn = (el, fromX = -30) => {
  if (!el) return;
  gsap.fromTo(el,
    { opacity: 0, x: fromX },
    { opacity: 1, x: 0, duration: 0.35, ease: "power2.out" }
  );
};

// ── Particle Physics Background Component ─────────────────────────────────────
function CursorPhysics({ theme }) {
  const canvasRef = useRef(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    let animationId;
    let width = (canvas.width = window.innerWidth);
    let height = (canvas.height = window.innerHeight);

    // Particle pool
    const particles = [];
    const maxParticles = 60;

    // Track mouse coordinates
    const mouse = { x: null, y: null, active: false };

    // Select color based on active theme
    const getParticleColor = () => {
      if (theme === "light") {
        return `rgba(99, 102, 241, ${Math.random() * 0.4 + 0.2})`; // Indigo
      } else if (theme === "navy") {
        return `rgba(224, 169, 109, ${Math.random() * 0.4 + 0.3})`; // Amber
      }
      return `rgba(124, 110, 249, ${Math.random() * 0.4 + 0.2})`; // Purple
    };

    class Particle {
      constructor(x, y) {
        this.x = x;
        this.y = y;
        this.size = Math.random() * 3 + 1;
        this.vx = (Math.random() - 0.5) * 1.5;
        this.vy = (Math.random() - 0.5) * 1.5;
        this.life = 1.0;
        this.decay = Math.random() * 0.015 + 0.008;
        this.color = getParticleColor();
      }

      update() {
        this.x += this.vx;
        this.y += this.vy;
        this.life -= this.decay;
      }

      draw() {
        ctx.beginPath();
        ctx.arc(this.x, this.y, this.size, 0, Math.PI * 2);
        ctx.fillStyle = this.color.replace(/[\d.]+\)$/, `${this.life})`);
        ctx.fill();
      }
    }

    const handleResize = () => {
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    };

    const handleMouseMove = (e) => {
      mouse.x = e.clientX;
      mouse.y = e.clientY;
      mouse.active = true;

      // Spawn particles
      if (particles.length < maxParticles) {
        for (let i = 0; i < 2; i++) {
          particles.push(new Particle(mouse.x, mouse.y));
        }
      }
    };

    const handleMouseLeave = () => {
      mouse.active = false;
    };

    window.addEventListener("resize", handleResize);
    window.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseleave", handleMouseLeave);

    // Loop
    const tick = () => {
      ctx.clearRect(0, 0, width, height);

      // Connect particles close to mouse or each other
      for (let i = 0; i < particles.length; i++) {
        particles[i].update();
        particles[i].draw();

        if (particles[i].life <= 0) {
          particles.splice(i, 1);
          i--;
          continue;
        }

        // Connections
        for (let j = i + 1; j < particles.length; j++) {
          const dx = particles[i].x - particles[j].x;
          const dy = particles[i].y - particles[j].y;
          const dist = Math.sqrt(dx * dx + dy * dy);

          if (dist < 80) {
            ctx.beginPath();
            ctx.moveTo(particles[i].x, particles[i].y);
            ctx.lineTo(particles[j].x, particles[j].y);
            // Dynamic transparency lines
            const alpha = (1 - dist / 80) * 0.15 * Math.min(particles[i].life, particles[j].life);
            ctx.strokeStyle = theme === "light" 
              ? `rgba(99, 102, 241, ${alpha})`
              : theme === "navy"
                ? `rgba(224, 169, 109, ${alpha})`
                : `rgba(124, 110, 249, ${alpha})`;
            ctx.lineWidth = 0.5;
            ctx.stroke();
          }
        }
      }

      animationId = requestAnimationFrame(tick);
    };

    tick();

    return () => {
      window.removeEventListener("resize", handleResize);
      window.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseleave", handleMouseLeave);
      cancelAnimationFrame(animationId);
    };
  }, [theme]);

  return <canvas id="cursor-physics-canvas" ref={canvasRef} />;
}

export default function ChatApp() {
  // Auth State
  const [token, setToken] = useState(localStorage.getItem("token") || "");
  const [username, setUsername] = useState(localStorage.getItem("username") || "");
  const [isRegistering, setIsRegistering] = useState(false);
  const [authError, setAuthError] = useState("");
  const [formData, setFormData] = useState({ username: "", password: "" });

  // Chat/Session State
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState("");
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [streamingText, setStreamingText] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(true);

  // Theme Settings
  const [theme, setTheme] = useState(localStorage.getItem("app-theme") || "dark");
  const [themeMenuOpen, setThemeMenuOpen] = useState(false);

  const bottomRef = useRef(null);
  const inputRef = useRef(null);
  const authCardRef = useRef(null);
  const sidebarRef = useRef(null);
  const chatShellRef = useRef(null);
  const messagesAreaRef = useRef(null);

  // Apply Theme to body class
  useEffect(() => {
    document.body.className = `theme-${theme}`;
    localStorage.setItem("app-theme", theme);
  }, [theme]);

  // ── Auto-scroll ─────────────────────────────────────────────────────────────
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingText, loading]);

  // ── Animate auth card on mount ──────────────────────────────────────────────
  useEffect(() => {
    if (!token && authCardRef.current) {
      gsap.fromTo(authCardRef.current,
        { opacity: 0, y: 40, scale: 0.95 },
        { opacity: 1, y: 0, scale: 1, duration: 0.6, ease: "back.out(1.7)", delay: 0.1 }
      );
    }
  }, [token]);

  // ── Animate main app on login ───────────────────────────────────────────────
  useEffect(() => {
    if (token) {
      if (sidebarRef.current) animateSlideIn(sidebarRef.current, -40);
      if (chatShellRef.current) {
        gsap.fromTo(chatShellRef.current,
          { opacity: 0 },
          { opacity: 1, duration: 0.5, delay: 0.1, ease: "power2.out" }
        );
      }
    }
  }, [token]);

  // ── Animate each new message row ─────────────────────────────────────────────
  useEffect(() => {
    const rows = messagesAreaRef.current?.querySelectorAll(".message-row");
    if (rows && rows.length > 0) {
      const last = rows[rows.length - 1];
      animateIn(last);
    }
  }, [messages.length]);

  // ── Fetch User Sessions ──────────────────────────────────────────────────────
  const fetchSessions = useCallback(async (authToken) => {
    try {
      const res = await fetch(`${API_BASE}/sessions`, {
        headers: { "Authorization": `Bearer ${authToken}` },
      });
      const data = await res.json();
      if (res.ok) {
        setSessions(data.sessions || []);
        if (data.sessions && data.sessions.length > 0 && !activeSessionId) {
          selectSession(data.sessions[0].id, authToken);
        }
      }
    } catch {
      setError("Failed to load conversation history.");
    }
  }, [activeSessionId]);

  const selectSession = async (sessionId, authToken = token) => {
    setActiveSessionId(sessionId);
    setStreamingText("");
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/sessions/${sessionId}`, {
        headers: { "Authorization": `Bearer ${authToken}` },
      });
      const data = await res.json();
      if (res.ok) {
        const loadedMsgs = (data.messages || []).map((msg) => ({
          ...msg,
          id: Math.random(),
          timestamp: new Date(msg.created_at || Date.now()),
        }));
        setMessages(loadedMsgs);
      }
    } catch {
      setError("Failed to fetch messages.");
    }
  };

  // ── Auth handlers ────────────────────────────────────────────────────────────
  const handleAuthChange = (e) => {
    setFormData((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    setAuthError("");
    try {
      const res = await fetch(`${API_BASE}/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      });
      const data = await res.json();
      if (res.ok) {
        localStorage.setItem("token", data.token);
        localStorage.setItem("username", data.user.username);
        setToken(data.token);
        setUsername(data.user.username);
        setFormData({ username: "", password: "" });
        fetchSessions(data.token);
      } else {
        setAuthError(data.error || "Login failed.");
        gsap.fromTo(authCardRef.current, { x: -8 }, { x: 0, duration: 0.4, ease: "elastic.out(1, 0.3)" });
      }
    } catch {
      setAuthError("Could not reach server.");
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setAuthError("");
    try {
      const res = await fetch(`${API_BASE}/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(formData),
      });
      const data = await res.json();
      if (res.ok) {
        setIsRegistering(false);
        setAuthError("Account created! Please log in.");
      } else {
        setAuthError(data.error || "Registration failed.");
      }
    } catch {
      setAuthError("Could not reach server.");
    }
  };

  const handleLogout = () => {
    gsap.to([sidebarRef.current, chatShellRef.current], {
      opacity: 0, y: -10, duration: 0.3, stagger: 0.05, ease: "power2.in",
      onComplete: () => {
        localStorage.clear();
        setToken(""); setUsername(""); setSessions([]);
        setActiveSessionId(""); setMessages([]);
      }
    });
  };

  // ── Session handlers ─────────────────────────────────────────────────────────
  const createNewSession = async () => {
    if (loading) return;
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/sessions`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ title: "New Conversation" }),
      });
      const data = await res.json();
      if (res.ok) {
        setSessions((prev) => [
          { id: data.session_id, title: data.title, created_at: new Date().toISOString() },
          ...prev,
        ]);
        selectSession(data.session_id);
      }
    } catch {
      setError("Failed to create session.");
    }
  };

  const handleDeleteSession = async (e, sessionId) => {
    e.stopPropagation();
    if (loading) return;
    try {
      const res = await fetch(`${API_BASE}/sessions/${sessionId}`, {
        method: "DELETE",
        headers: { "Authorization": `Bearer ${token}` },
      });
      if (res.ok) {
        setSessions((prev) => prev.filter((s) => s.id !== sessionId));
        if (activeSessionId === sessionId) { setMessages([]); setActiveSessionId(""); }
      }
    } catch { setError("Failed to delete session."); }
  };

  // ── Send message (SSE streaming) ─────────────────────────────────────────────
  const sendMessage = async (text) => {
    const trimmed = (text ?? input).trim();
    if (!trimmed || loading || !activeSessionId) return;

    setError(null);
    setInput("");
    setLoading(true);
    setStreamingText("");

    const userMsg = { id: Math.random(), role: "user", content: trimmed, timestamp: new Date() };
    setMessages((prev) => [...prev, userMsg]);

    try {
      const res = await fetch(`${API_BASE}/chat/stream`, {
        method: "POST",
        headers: { "Authorization": `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify({ message: trimmed, session_id: activeSessionId }),
      });

      if (!res.ok) {
        const errorData = await res.json();
        setError(errorData.error || "Stream failed.");
        setLoading(false);
        return;
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let completeResponse = "";
      let metadata = {};

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        const lines = decoder.decode(value).split("\n");
        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.chunk) { completeResponse += data.chunk; setStreamingText(completeResponse); }
              else if (data.done) { metadata = { tokens_used: data.tokens_used, latency_ms: data.latency_ms }; }
              else if (data.error) setError(data.error);
            } catch { /* partial buffer, ignore */ }
          }
        }
      }

      setMessages((prev) => [...prev, {
        id: Math.random(), role: "assistant", content: completeResponse,
        timestamp: new Date(), ...metadata,
      }]);
      setStreamingText("");
      fetchSessions(token);
    } catch {
      setError("Network error while streaming.");
    } finally {
      setLoading(false);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  };

  useEffect(() => { if (token) fetchSessions(token); }, [token]);

  // ── Render: Auth Screen ──────────────────────────────────────────────────────
  if (!token) {
    return (
      <main className="auth-container">
        <CursorPhysics theme={theme} />
        <div className="auth-particle-bg" aria-hidden="true" />
        <div className="auth-card" ref={authCardRef}>
          <div className="brand-logo">
            <div className="logo-ring" />
            <span className="logo-icon">⚡</span>
          </div>
          <h1 className="brand-name">MemoryAgent</h1>
          <p className="auth-tagline">An AI that actually remembers you.</p>
          <p className="auth-mode-label">
            {isRegistering ? "Create your account" : "Welcome back"}
          </p>

          {authError && <div className="auth-error">{authError}</div>}

          <form onSubmit={isRegistering ? handleRegister : handleLogin}>
            <div className="form-group">
              <label htmlFor="username">Username</label>
              <input type="text" id="username" name="username" required
                value={formData.username} onChange={handleAuthChange}
                placeholder="Enter your username" autoComplete="username" />
            </div>
            <div className="form-group">
              <label htmlFor="password">Password</label>
              <input type="password" id="password" name="password" required
                value={formData.password} onChange={handleAuthChange}
                placeholder="Enter your password" autoComplete={isRegistering ? "new-password" : "current-password"} />
            </div>
            <button type="submit" className="btn-auth-submit">
              {isRegistering ? "Create Account" : "Sign In"}
            </button>
          </form>

          <button className="btn-auth-switch"
            onClick={() => { setIsRegistering(!isRegistering); setAuthError(""); }}>
            {isRegistering ? "Already have an account? Sign in" : "Don't have an account? Register"}
          </button>

          <div className="auth-footer-badges">
            <span className="badge">⚡ Groq Llama 3</span>
            <span className="badge">🔐 JWT Secured</span>
            <span className="badge">🧠 Memory-Enabled</span>
          </div>
        </div>
      </main>
    );
  }

  // ── Render: Main App ─────────────────────────────────────────────────────────
  return (
    <>
      <CursorPhysics theme={theme} />

      <div className="app-bg" aria-hidden="true">
        <div className="bg-orb orb-1" />
        <div className="bg-orb orb-2" />
        <div className="bg-orb orb-3" />
      </div>

      <div className="app-container">
        {/* ── Sidebar ── */}
        <aside className={`sidebar ${sidebarOpen ? "open" : "closed"}`} ref={sidebarRef}>
          <div className="sidebar-brand">
            <span className="sidebar-logo">⚡</span>
            <span className="sidebar-app-name">MemoryAgent</span>
          </div>

          <div className="sidebar-header">
            <button className="btn-new-chat" onClick={createNewSession}>
              <span className="btn-new-chat-icon">+</span>
              New Chat
            </button>
          </div>

          <nav className="sessions-list">
            <div className="list-title">Conversations</div>
            {sessions.length === 0 && (
              <div className="sessions-empty">No conversations yet</div>
            )}
            {sessions.map((s) => (
              <div key={s.id}
                className={`session-item ${s.id === activeSessionId ? "active" : ""}`}
                onClick={() => selectSession(s.id)}
              >
                <span className="chat-icon">💬</span>
                <span className="session-title">{s.title}</span>
                <button className="btn-delete-session"
                  onClick={(e) => handleDeleteSession(e, s.id)} title="Delete">✕</button>
              </div>
            ))}
          </nav>

          <div className="sidebar-footer">
            <div className="user-profile">
              <div className="avatar-letter">{username[0]?.toUpperCase() || "U"}</div>
              <div className="user-info">
                <span className="username">{username}</span>
                <span className="user-sub">AI Engineer</span>
              </div>
            </div>
            <button className="btn-logout" onClick={handleLogout}>↩</button>
          </div>
        </aside>

        {/* ── Main Chat Area ── */}
        <main className="chat-shell" ref={chatShellRef}>
          <header className="chat-header">
            <div className="header-left">
              <button className="btn-sidebar-toggle" onClick={() => setSidebarOpen(!sidebarOpen)}>
                ☰
              </button>
              <div className="header-meta">
                <h2>MemoryAgent</h2>
                <div className="subtitle">Groq Llama 3 · Stateful Memory · JWT Auth</div>
              </div>
            </div>
            <div className="header-right">
              {/* Theme Selector Trigger */}
              <div className="theme-selector-wrap">
                <button className="btn-theme-trigger" onClick={() => setThemeMenuOpen(!themeMenuOpen)}>
                  🎨 Theme: {theme.charAt(0).toUpperCase() + theme.slice(1)}
                </button>
                {themeMenuOpen && (
                  <div className="theme-dropdown" onMouseLeave={() => setThemeMenuOpen(false)}>
                    <button className={`theme-option ${theme === "dark" ? "active" : ""}`}
                      onClick={() => { setTheme("dark"); setThemeMenuOpen(false); }}>
                      💜 Dark Mode {theme === "dark" && "✓"}
                    </button>
                    <button className={`theme-option ${theme === "light" ? "active" : ""}`}
                      onClick={() => { setTheme("light"); setThemeMenuOpen(false); }}>
                      ☀️ Light Mode {theme === "light" && "✓"}
                    </button>
                    <button className={`theme-option ${theme === "navy" ? "active" : ""}`}
                      onClick={() => { setTheme("navy"); setThemeMenuOpen(false); }}>
                      🎖️ Navy Commando {theme === "navy" && "✓"}
                    </button>
                  </div>
                )}
              </div>

              <div className="status-pill">
                <span className="status-dot" />
                Live
              </div>
            </div>
          </header>

          <section className="messages-area" ref={messagesAreaRef}>
            {messages.length === 0 && !streamingText ? (
              <div className="empty-state">
                <div className="empty-icon-ring">
                  <span className="empty-icon">⚡</span>
                </div>
                <h2>Start a conversation</h2>
                <p>MemoryAgent remembers everything you tell it within a session.<br />
                  Create a new chat in the sidebar and start talking.</p>
                <div className="starter-chips">
                  {["What can you help me with?", "Tell me about yourself", "Explain memory in AI systems"].map((chip) => (
                    <button key={chip} className="chip"
                      onClick={() => sendMessage(chip)}>{chip}</button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((msg) => (
                <div key={msg.id} className={`message-row ${msg.role}`}>
                  <div className={`msg-avatar ${msg.role}`}>
                    {msg.role === "user" ? username[0]?.toUpperCase() || "U" : "⚡"}
                  </div>
                  <div className="bubble-wrap">
                    <div className={`bubble ${msg.role}`}>{msg.content}</div>
                    <div className="msg-meta-row">
                      <span className="msg-time">
                        {new Date(msg.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </span>
                      {msg.role === "assistant" && msg.tokens_used > 0 && (
                        <span className="token-badge">
                          🪙 {msg.tokens_used} · ⚡ {Math.round(msg.latency_ms)}ms
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}

            {streamingText && (
              <div className="message-row assistant streaming">
                <div className="msg-avatar assistant">⚡</div>
                <div className="bubble-wrap">
                  <div className="bubble assistant">{streamingText}<span className="cursor-blink">|</span></div>
                  <div className="streaming-label">Generating...</div>
                </div>
              </div>
            )}

            {loading && !streamingText && (
              <div className="message-row assistant">
                <div className="msg-avatar assistant">⚡</div>
                <div className="bubble-wrap">
                  <div className="typing-bubble">
                    <span className="dot" /><span className="dot" /><span className="dot" />
                  </div>
                </div>
              </div>
            )}

            {error && <div className="error-banner">⚠️ {error}</div>}
            <div ref={bottomRef} />
          </section>

          <footer className="input-area">
            {!activeSessionId && (
              <div className="no-session-hint">
                ← Select a conversation or click "New Chat" to begin
              </div>
            )}
            <div className="input-row">
              <textarea
                id="message-input"
                ref={inputRef}
                className="msg-input"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
                }}
                placeholder={activeSessionId ? "Message MemoryAgent..." : "Select a session first..."}
                disabled={loading || !activeSessionId}
                rows={1}
              />
              <button id="btn-send" className="btn-send"
                onClick={() => sendMessage()}
                disabled={loading || !input.trim() || !activeSessionId}>
                {loading ? <span className="spinner" /> : "↑"}
              </button>
            </div>
            <div className="footer-bar">
              <span className="model-tag">⚡ llama-3.3-70b-versatile · DecodeLabs</span>
              <span className="footer-note">Enter to send · Shift+Enter for newline</span>
            </div>
          </footer>
        </main>
      </div>
    </>
  );
}
