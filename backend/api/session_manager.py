import sqlite3
import uuid
import time
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
            context TEXT,
            sources TEXT,
            trace TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
        )
    ''')
    
    conn.commit()
    conn.close()

def create_session(workspace: str = "vistastream") -> str:
    session_id = str(uuid.uuid4())
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO sessions (id, title, workspace) VALUES (?, ?, ?)",
        (session_id, "New Chat", workspace)
    )
    conn.commit()
    conn.close()
    return session_id

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

def add_message(session_id: str, role: str, content: str, context: str = None, sources: str = None, trace: str = None):
    msg_id = str(uuid.uuid4())
    conn = get_db_connection()
    
    conn.execute(
        "INSERT INTO messages (id, session_id, role, content, context, sources, trace) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (msg_id, session_id, role, content, context, sources, trace)
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
