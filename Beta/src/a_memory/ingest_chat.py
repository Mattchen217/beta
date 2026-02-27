import json
from src.a_memory.db import init_db, connect
from src.a_memory.config import DATA_DIR

def ingest(json_path: str):
    init_db()
    conn = connect()
    cur = conn.cursor()

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for conv in data["conversations"]:
        conv_id = conv["conv_id"]
        title = conv.get("title", "")
        participants = ",".join(conv.get("participants", []))
        last_ts = conv["messages"][-1]["ts"] if conv["messages"] else None

        cur.execute("""
            INSERT OR REPLACE INTO conversations(conv_id, title, participants, last_active_ts)
            VALUES(?,?,?,?)
        """, (conv_id, title, participants, last_ts))

        for m in conv["messages"]:
            cur.execute("""
                INSERT OR REPLACE INTO messages(id, conv_id, sender, ts, text)
                VALUES(?,?,?,?,?)
            """, (m["id"], conv_id, m["sender"], m["ts"], m["text"]))

    conn.commit()
    conn.close()
    print("✅ Ingest done")

if __name__ == "__main__":
    ingest(str(DATA_DIR / "chat_sample.json"))