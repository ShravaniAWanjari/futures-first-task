import sqlite3
import uuid
import time
import secrets
from typing import List, Dict, Any, Optional
from backend.config import Config

def get_db_connection():
    conn = sqlite3.connect(Config.SESSIONS_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_sessions_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Sessions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            title TEXT,
            workspace TEXT,
            secret TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Messages table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id TEXT PRIMARY KEY,
            session_id TEXT,
            role TEXT,
            content TEXT,
            image TEXT,
            context TEXT,
            sources TEXT,
            trace TEXT,
            structured_data TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
        )
    ''')
    
    # Migration: Add image column if it doesn't exist (Phase 11.2)
    try:
        cursor.execute("ALTER TABLE messages ADD COLUMN image TEXT")
    except sqlite3.OperationalError:
        pass # Already exists
    
    conn.commit()
    conn.close()

def create_session(workspace: str = "vistastream") -> dict:
    session_id = str(uuid.uuid4())
    session_secret = secrets.token_urlsafe(32)
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO sessions (id, title, workspace, secret) VALUES (?, ?, ?, ?)",
        (session_id, "New Chat", workspace, session_secret)
    )
    conn.commit()
    conn.close()
    return {"session_id": session_id, "session_secret": session_secret}

def validate_session_secret(session_id: str, secret: str) -> bool:
    """Phase 3: Lightweight session ownership validation."""
    conn = get_db_connection()
    row = conn.execute("SELECT secret FROM sessions WHERE id = ?", (session_id,)).fetchone()
    conn.close()
    if not row:
        return False
    stored_secret = row["secret"]
    # If no secret stored (legacy session), allow access
    if not stored_secret:
        return True
    return secrets.compare_digest(stored_secret, secret)

def list_sessions(workspace: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    if workspace:
        rows = conn.execute(
            "SELECT * FROM sessions WHERE workspace = ? ORDER BY updated_at DESC", 
            (workspace,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM sessions ORDER BY updated_at DESC").fetchall()
    sessions = [dict(row) for row in rows]
    conn.close()
    return sessions

def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    if not row:
        conn.close()
        return None
    
    session = dict(row)
    # Get messages
    msg_rows = conn.execute(
        "SELECT * FROM messages WHERE session_id = ? ORDER BY timestamp ASC",
        (session_id,)
    ).fetchall()
    session["messages"] = [dict(msg) for msg in msg_rows]
    
    conn.close()
    return session

def delete_session(session_id: str):
    conn = get_db_connection()
    conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()

def update_session_title(session_id: str, title: str):
    conn = get_db_connection()
    conn.execute(
        "UPDATE sessions SET title = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (title, session_id)
    )
    conn.commit()
    conn.close()

def add_message(session_id: str, role: str, content: str, image: Optional[str] = None, context: str = None, sources: str = None, trace: str = None, structured_data: str = None):
    msg_id = str(uuid.uuid4())
    conn = get_db_connection()
    
    conn.execute(
        "INSERT INTO messages (id, session_id, role, content, image, context, sources, trace, structured_data) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (msg_id, session_id, role, content, image, context, sources, trace, structured_data)
    )
    conn.execute("UPDATE sessions SET updated_at = CURRENT_TIMESTAMP WHERE id = ?", (session_id,))
    
    conn.commit()
    conn.close()
    return msg_id

def get_session_messages(session_id: str) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT * FROM messages WHERE session_id = ? ORDER BY timestamp ASC",
        (session_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
