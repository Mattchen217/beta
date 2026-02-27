import sqlite3
from src.a_memory.config import DB_PATH

def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS conversations (
        conv_id TEXT PRIMARY KEY,
        title TEXT,
        participants TEXT,
        last_active_ts TEXT
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id TEXT PRIMARY KEY,
        conv_id TEXT,
        sender TEXT,
        ts TEXT,
        text TEXT,
        FOREIGN KEY(conv_id) REFERENCES conversations(conv_id)
    )
    """)
    conn.commit()
    conn.close()