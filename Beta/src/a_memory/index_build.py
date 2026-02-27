# src/index_build.py
import pickle
import numpy as np
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

from src.a_memory.db import connect
from src.a_memory.chunking import build_chunks, Chunk
from src.a_memory.config import (
    EMBEDDING_MODEL,
    DATA_DIR,
    BM25_PATH,
    CHUNKS_PATH,
)

# 你需要在 src/config.py 里加一行：
# EMBEDDINGS_PATH = DATA_DIR / "embeddings.npy"
from src.a_memory.config import EMBEDDINGS_PATH
from src.a_memory.preprocess import tokenize_for_bm25


def build():
    # 1) 读库：取全部会话
    conn = connect()
    cur = conn.cursor()

    cur.execute("SELECT conv_id FROM conversations")
    conv_ids = [r[0] for r in cur.fetchall()]

    # 2) 生成 chunks
    all_chunks: list[Chunk] = []
    for cid in conv_ids:
        cur.execute(
            "SELECT id, conv_id, sender, ts, text FROM messages WHERE conv_id=? ORDER BY ts",
            (cid,),
        )
        rows = cur.fetchall()
        msgs = [
            {"id": r[0], "conv_id": r[1], "sender": r[2], "ts": r[3], "text": r[4]}
            for r in rows
        ]
        all_chunks.extend(build_chunks(cid, msgs))

    conn.close()

    print(f"✅ chunks: {len(all_chunks)}")
    if not all_chunks:
        print("⚠️ 没有可用chunks。请先运行 ingest_chat.py 并确认 chat_sample.json 有内容。")
        return

    # 3) Embedding（normalize_embeddings=True -> 后续点积=余弦）
    model = SentenceTransformer(EMBEDDING_MODEL)
    texts = [c.text for c in all_chunks]

    embeddings = model.encode(
        texts,
        batch_size=32,
        show_progress_bar=True,
        normalize_embeddings=True,
    )
    embeddings = np.asarray(embeddings, dtype="float32")
    print("✅ embeddings shape:", embeddings.shape)

    # 4) BM25（关键词检索）
    tokenized = [tokenize_for_bm25(t) for t in texts]
    bm25 = BM25Okapi(tokenized)

    # 5) 落盘（确保目录存在）
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # 保存 embeddings.npy
    np.save(str(EMBEDDINGS_PATH), embeddings)
    print("✅ saved embeddings:", EMBEDDINGS_PATH)

    # 保存 bm25.pkl
    with open(BM25_PATH, "wb") as f:
        pickle.dump(bm25, f)
    print("✅ saved bm25:", BM25_PATH)

    # 保存 chunks.pkl
    with open(CHUNKS_PATH, "wb") as f:
        pickle.dump(all_chunks, f)
    print("✅ saved chunks:", CHUNKS_PATH)

    print("✅ index built (no faiss).")


if __name__ == "__main__":
    build()