# file: src/a_memory/config.py
from pathlib import Path

# src/a_memory/config.py → project_root
BASE_DIR = Path(__file__).resolve().parents[2]

DATA_DIR = BASE_DIR / "data"

# ---- storage ----
DB_PATH = DATA_DIR / "memory.db"
FAISS_INDEX_PATH = DATA_DIR / "faiss.index"
BM25_PATH = DATA_DIR / "bm25.pkl"
CHUNKS_PATH = DATA_DIR / "chunks.pkl"
EMBEDDINGS_PATH = DATA_DIR / "embeddings.npy"

# ---- models ----
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# ---- chunking ----
MIN_TEXT_LEN = 4        # ⭐ 建议降低，避免短关键事实丢失
MAX_CHUNK_CHARS = 1000  # ⭐ 稍微放宽，减少过度切分