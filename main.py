from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import sqlite3, os, json
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = os.environ.get("DB_PATH", "/data/drinks.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            start INTEGER NOT NULL,
            created_at INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS drinks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
            raw TEXT NOT NULL,
            ts INTEGER NOT NULL,
            type TEXT NOT NULL,
            abv REAL NOT NULL,
            oz REAL NOT NULL,
            bac REAL NOT NULL,
            std_total REAL NOT NULL,
            reply_opener TEXT NOT NULL,
            reply_bac_str TEXT NOT NULL,
            reply_std TEXT NOT NULL,
            reply_closer TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()

init_db()

# --- models ---

class SessionCreate(BaseModel):
    name: str
    start: int

class SessionRename(BaseModel):
    name: str

class DrinkCreate(BaseModel):
    raw: str
    ts: int
    type: str
    abv: float
    oz: float
    bac: float
    std_total: float
    reply_opener: str
    reply_bac_str: str
    reply_std: str
    reply_closer: str

# --- sessions ---

@app.get("/api/sessions")
def list_sessions():
    conn = get_db()
    sessions = conn.execute("SELECT * FROM sessions ORDER BY start DESC").fetchall()
    result = []
    for s in sessions:
        drinks = conn.execute(
            "SELECT * FROM drinks WHERE session_id = ? ORDER BY ts ASC", (s["id"],)
        ).fetchall()
        result.append({
            "id": s["id"],
            "name": s["name"],
            "start": s["start"],
            "drinks": [dict(d) for d in drinks]
        })
    conn.close()
    return result

@app.post("/api/sessions")
def create_session(body: SessionCreate):
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO sessions (name, start, created_at) VALUES (?, ?, ?)",
        (body.name, body.start, int(datetime.now().timestamp() * 1000))
    )
    conn.commit()
    session_id = cur.lastrowid
    conn.close()
    return {"id": session_id, "name": body.name, "start": body.start, "drinks": []}

@app.patch("/api/sessions/{session_id}")
def rename_session(session_id: int, body: SessionRename):
    conn = get_db()
    conn.execute("UPDATE sessions SET name = ? WHERE id = ?", (body.name, session_id))
    conn.commit()
    conn.close()
    return {"ok": True}

@app.delete("/api/sessions/{session_id}")
def delete_session(session_id: int):
    conn = get_db()
    conn.execute("DELETE FROM drinks WHERE session_id = ?", (session_id,))
    conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()
    return {"ok": True}

# --- drinks ---

@app.post("/api/sessions/{session_id}/drinks")
def add_drink(session_id: int, body: DrinkCreate):
    conn = get_db()
    s = conn.execute("SELECT id FROM sessions WHERE id = ?", (session_id,)).fetchone()
    if not s:
        raise HTTPException(status_code=404, detail="session not found")
    cur = conn.execute(
        """INSERT INTO drinks
           (session_id, raw, ts, type, abv, oz, bac, std_total,
            reply_opener, reply_bac_str, reply_std, reply_closer)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
        (session_id, body.raw, body.ts, body.type, body.abv, body.oz,
         body.bac, body.std_total, body.reply_opener, body.reply_bac_str,
         body.reply_std, body.reply_closer)
    )
    conn.commit()
    drink_id = cur.lastrowid
    conn.close()
    return {"id": drink_id}
