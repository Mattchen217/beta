# src/search.py
import pickle
import numpy as np
from sentence_transformers import SentenceTransformer
from dateutil.parser import isoparse
from src.a_memory.db import connect

from src.a_memory.config import (
    EMBEDDING_MODEL,
    BM25_PATH,
    CHUNKS_PATH,
    EMBEDDINGS_PATH,
)

from src.a_memory.preprocess import tokenize_for_bm25, normalize_text

def time_overlap(chunk_start: str, chunk_end: str, q_start: str | None, q_end: str | None) -> bool:
    """
    判断 chunk 时间区间是否与查询时间区间重叠。
    - q_start/q_end 为空则视为无限范围
    """
    cs = isoparse(chunk_start)
    ce = isoparse(chunk_end)
    if q_start:
        qs = isoparse(q_start)
    else:
        qs = None
    if q_end:
        qe = isoparse(q_end)
    else:
        qe = None

    if qs and ce < qs:
        return False
    if qe and cs > qe:
        return False
    return True

def fetch_messages_by_ids(ids: list[str]):
    conn = connect()
    cur = conn.cursor()
    q = ",".join(["?"] * len(ids))
    cur.execute(f"SELECT id, sender, ts, text FROM messages WHERE id IN ({q})", ids)
    rows = cur.fetchall()
    conn.close()
    # 按 ts 排序
    rows.sort(key=lambda r: r[2])
    return [{"id": r[0], "sender": r[1], "ts": r[2], "text": r[3]} for r in rows]

class MemorySearch:
    def __init__(self):
        self.model = SentenceTransformer(EMBEDDING_MODEL)

        with open(BM25_PATH, "rb") as f:
            self.bm25 = pickle.load(f)

        with open(CHUNKS_PATH, "rb") as f:
            self.chunks = pickle.load(f)

        self.embeddings = np.load(str(EMBEDDINGS_PATH)).astype("float32")
        if len(self.chunks) != self.embeddings.shape[0]:
            raise RuntimeError(
                f"chunks数量({len(self.chunks)}) 与 embeddings行数({self.embeddings.shape[0]}) 不一致，"
                "请重新运行 index_build.py"
            )

    def search(
        self,
        query: str,
        top_k: int = 5,
        conv_id: str | None = None,
        start_ts: str | None = None,
        end_ts: str | None = None,
    ):
        if not self.chunks:
            return []

        # ===== 1) 向量检索：点积=余弦（因为建库时 normalize_embeddings=True）=====
        q = self.model.encode([normalize_text(query)], normalize_embeddings=True).astype("float32")[0]
        vec_scores = self.embeddings @ q  # shape=(N,)

        # 先取全局 top50，再做过滤（MVP 简化）
        top50 = vec_scores.argsort()[-50:][::-1]

        vec_hits = []
        for idx in top50:
            c = self.chunks[idx]
            if conv_id and c.conv_id != conv_id:
                continue
            if not time_overlap(c.time_start, c.time_end, start_ts, end_ts):
                continue
            vec_hits.append((idx, float(vec_scores[idx])))

        # ===== 2) BM25 关键词召回（同样过滤）=====
        bm_scores = self.bm25.get_scores(tokenize_for_bm25(query))
        # 取 top50
        bm_top = np.argsort(bm_scores)[-50:][::-1]

        bm_hits = []
        for idx in bm_top:
            c = self.chunks[idx]
            if conv_id and c.conv_id != conv_id:
                continue
            if not time_overlap(c.time_start, c.time_end, start_ts, end_ts):
                continue
            bm_hits.append((idx, float(bm_scores[idx])))

        # ===== 3) 融合排序 =====
        # 归一化 bm25
        bm_max = float(np.max(bm_scores)) if np.max(bm_scores) > 0 else 1.0

        score_map = {}
        for idx, s in vec_hits:
            score_map[idx] = score_map.get(idx, 0.0) + 0.6 * s
        for idx, s in bm_hits:
            score_map[idx] = score_map.get(idx, 0.0) + 0.4 * (s / bm_max)

        ranked = sorted(score_map.items(), key=lambda x: x[1], reverse=True)[:top_k]

        results = []
        for idx, s in ranked:
            c = self.chunks[idx]
            conf = "高" if s > 0.8 else ("中" if s > 0.5 else "低")
            results.append(
                {
                    "chunk_id": c.chunk_id,
                    "conv_id": c.conv_id,
                    "time_range": (c.time_start, c.time_end),
                    "score": float(s),
                    "confidence": conf,
                    "text": c.text,
                    "message_ids": c.message_ids,
                }
            )
        return results

