
from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any, Dict, List, Optional, Tuple

from src.a_memory.search import MemorySearch
from src.a_memory.db import connect

from src.b_answer.qwen_answer import QwenEvidenceAnswerer, EvidenceBlock
from src.b_style.api import style_rewrite
from src.b_style.style_profile import StyleProfile
from src.b_style.adapter.apply import StyleAdapter


def fetch_conv_meta(conv_id: str) -> Dict[str, Any]:
    """
    从 SQLite 中取会话 title/participants 等元信息。
    A 的检索结果里只有 conv_id，需要在这里补上 title 才能“像助手”回答。
    """
    try:
        conn = connect()
        cur = conn.cursor()
        cur.execute("SELECT title, participants, last_active_ts FROM conversations WHERE conv_id = ?", (conv_id,))
        row = cur.fetchone()
        conn.close()
        if not row:
            return {"title": "", "participants": "", "last_active_ts": ""}
        return {"title": row[0] or "", "participants": row[1] or "", "last_active_ts": row[2] or ""}
    except Exception:
        return {"title": "", "participants": "", "last_active_ts": ""}


@dataclass
class CopilotResult:
    final_answer: str
    raw_answer: str
    memory_trace: List[Dict[str, Any]]
    style_trace: Dict[str, Any]


class CopilotAgentABC:
    """
    你拍板的 ABC：
    A（取证据） -> B（基于证据生成回答） -> C（adapter 风格润色）

    说明：
    - A：复用现有 src/a_memory/search.py 的 MemorySearch（向量 + BM25 融合）
    - B：Qwen base 生成“助手式答案”，并强制输出“依据”
    - C：style_rewrite（规则 + 可选 LoRA），默认在 QA 类 intent 下关闭 sign_off，避免乱加尾巴
    """
    def __init__(
        self,
        profile: StyleProfile,
        base_model: str = "google/gemma-3-1b-it",
        adapter: Optional[StyleAdapter] = None,
    ):
        self.profile = profile
        self.adapter = adapter

        # A
        self.search = MemorySearch()

        # B
        self.answerer = QwenEvidenceAnswerer(base_model=base_model)

    def _build_evidence_blocks(self, results: List[Dict[str, Any]]) -> List[EvidenceBlock]:
        blocks: List[EvidenceBlock] = []
        for i, r in enumerate(results, 1):
            conv_id = r.get("conv_id", "")
            meta = fetch_conv_meta(conv_id)
            blocks.append(
                EvidenceBlock(
                    idx=i,
                    conv_id=conv_id,
                    conv_title=meta.get("title", ""),
                    time_range=r.get("time_range"),
                    message_ids=list(r.get("message_ids") or []),
                    score=float(r.get("score", 0.0)),
                    confidence=r.get("confidence", ""),
                    snippet=(r.get("text") or "")[:800],
                )
            )
        return blocks

    def answer(self, question: str, top_k: int = 5, mode: str = "self_qa") -> CopilotResult:
        """
        mode:
          - self_qa: 自己问自己（不走 style adaptor / LoRA）
          - external_reply: 对外回复（走 style adaptor / LoRA）
        """
        t0 = time.perf_counter()

        # ---------- A: retrieve evidence ----------
        raw_results = self.search.search(question, top_k=top_k)
        t1 = time.perf_counter()

        evidences = self._build_evidence_blocks(raw_results)

        memory_trace: List[Dict[str, Any]] = []
        for ev in evidences:
            memory_trace.append(
                {
                    "idx": ev.idx,
                    "conv_title": ev.conv_title,
                    "conv_id": ev.conv_id,
                    "time_range": ev.time_range,
                    "msg_ids": ev.message_ids,
                    "score": ev.score,
                    "confidence": ev.confidence,
                    "snippet": ev.snippet,
                }
            )

        # ---------- B: generate answer grounded on evidence ----------
        raw_answer = self.answerer.answer(question=question, evidences=evidences)
        t2 = time.perf_counter()

        timing_ms = {
            "A_retrieval": int((t1 - t0) * 1000),
            "B_answer": int((t2 - t1) * 1000),
            "C_style": 0,
            "total": int((t2 - t0) * 1000),
        }

        # ---------- C: style adapter polish (ONLY for external_reply) ----------
        if mode != "external_reply" or self.adapter is None:
            # ✅ 自己问自己：不通过 adaptor，直接输出 B 的结果
            return CopilotResult(
                final_answer=raw_answer,
                raw_answer=raw_answer,
                memory_trace=memory_trace,
                style_trace={"applied": False, "meta": {"mode": mode, "adapter": False, "timing_ms": timing_ms}},
            )

        # ✅ 对外：走 b_style（规则→LoRA→invariants→diff）
        signoff_backup = self.profile.sign_off.enabled

        styled_res = style_rewrite(
            draft_reply=raw_answer,
            profile=self.profile,
            intent="customer_support_reply",
            adapter=self.adapter,
            force=True,
        )
        t3 = time.perf_counter()

        self.profile.sign_off.enabled = signoff_backup

        timing_ms["C_style"] = int((t3 - t2) * 1000)
        timing_ms["total"] = int((t3 - t0) * 1000)

        style_trace = {
            "applied": styled_res.applied,
            "ok_invariants": styled_res.ok_invariants,
            "violations": [v.detail for v in styled_res.violations],
            "diff": styled_res.diff.to_dict(),
            "meta": {**styled_res.meta, "mode": mode, "adapter": True, "timing_ms": timing_ms},
        }

        return CopilotResult(
            final_answer=styled_res.styled_reply,
            raw_answer=raw_answer,
            memory_trace=memory_trace,
            style_trace=style_trace,
        )
