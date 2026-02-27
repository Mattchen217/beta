from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import time
import re
import pickle


from src.copilot.agent_abc import CopilotAgentABC, CopilotResult

app = FastAPI(title="HetaiAI Beta API")

UI_DIR = Path(__file__).parent / "ui"
app.mount("/assets", StaticFiles(directory=UI_DIR / "assets"), name="assets")

@app.get("/")
def root():
    return FileResponse(UI_DIR / "index.html")

# 你的项目里 profile/adapter 可选；为了最稳先 None
AGENT = CopilotAgentABC(profile=None, adapter=None)

# ---------- helpers ----------
ANSWER_RE = re.compile(r"(?s)^\s*Answer:\s*(.*?)\s*(?:\nEvidence:\s*.*)?$")
EVID_REF_RE = re.compile(r"\[\s*(\d+)\s*\]")

def _extract_answer_text(final_answer: str) -> str:
    s = (final_answer or "").strip()
    m = ANSWER_RE.match(s)
    if m:
        return (m.group(1) or "").strip()
    # fallback: 如果没有 Answer: 前缀，就直接返回原文
    return s

def _extract_cited_indices(final_answer: str) -> List[int]:
    # 从 Evidence 段落中提取类似 "- [1] ..." 的引用
    return sorted({int(x) for x in EVID_REF_RE.findall(final_answer or "")})

def _safe_time_range(tr):
    if not tr:
        return ""
    try:
        return f"{tr[0]} ~ {tr[1]}"
    except Exception:
        return str(tr)

def _timing_from_result(res: CopilotResult) -> Dict[str, float]:
    # agent_abc.py 里 timing_ms 放在 style_trace["meta"]["timing_ms"]
    try:
        meta = res.style_trace.get("meta", {}) if isinstance(res.style_trace, dict) else {}
        t = meta.get("timing_ms", None)
        if isinstance(t, dict):
            return t
    except Exception:
        pass
    return {}

# ---------- API schemas ----------
class ChatReq(BaseModel):
    user_id: str = "demo"
    mode: int = 1  # 1=self_qa 2=external_reply
    question: str
    extra: Optional[Dict[str, Any]] = None

class CitedMemory(BaseModel):
    idx: int
    conv_title: str
    conv_id: str
    time_range: str
    msg_ids: List[str]
    score: float
    confidence: str
    snippet: str

class ChatResp(BaseModel):
    answer: str
    cited_memories: List[CitedMemory]
    timing_ms: Dict[str, float]


# ---------- conversations (sample data) ----------
from functools import lru_cache
import json
from fastapi import HTTPException

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
CHAT_SAMPLE_PATH = DATA_DIR / "chat_sample.json"

@lru_cache(maxsize=1)
def _load_chat_sample() -> Dict[str, Any]:
    if not CHAT_SAMPLE_PATH.exists():
        return {"conversations": []}
    with open(CHAT_SAMPLE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def _conv_summary(conv: Dict[str, Any]) -> Dict[str, Any]:
    msgs = conv.get("messages") or []
    last = msgs[-1] if msgs else {}
    last_text = str(last.get("text") or "")
    # attachments simple marker
    if last.get("attachments"):
        att0 = last["attachments"][0]
        last_text = f"📎 {att0.get('name','attachment')}"
    last_ts = str(last.get("ts") or "")
    participants = conv.get("participants") or []
    return {
        "conv_id": conv.get("conv_id"),
        "title": conv.get("title") or "",
        "participants": participants,
        "is_group": len(participants) > 2,
        "last_ts": last_ts,
        "last_text": last_text,
    }

# ---------- routes ----------
@app.get("/health")
def health():
    return {"ok": True}


@app.get("/api/conversations")
def list_conversations():
    data = _load_chat_sample()
    convs = data.get("conversations") or []
    # keep file order
    return {"conversations": [_conv_summary(c) for c in convs]}

@app.get("/api/conversations/{conv_id}")
def get_conversation(conv_id: str):
    data = _load_chat_sample()
    for c in data.get("conversations") or []:
        if c.get("conv_id") == conv_id:
            return c
    raise HTTPException(status_code=404, detail="conversation not found")


@app.post("/chat", response_model=ChatResp)
def chat(req: ChatReq):
    t0 = time.perf_counter()

    mode_str = "self_qa" if req.mode == 1 else "external_reply"
    res = AGENT.answer(question=req.question, mode=mode_str)

    t1 = time.perf_counter()

    # 1) 只要 Answer 文本
    answer_text = _extract_answer_text(res.final_answer)

    # 2) 找到被引用的 memory idx
    cited = _extract_cited_indices(res.final_answer)

    # 3) 只返回被引用的那几条记忆（如果解析不到引用，就返回 top1）
    mem = res.memory_trace or []
    mem_by_idx = {m.get("idx"): m for m in mem if isinstance(m, dict)}
    if cited:
        chosen = [mem_by_idx[i] for i in cited if i in mem_by_idx]
    else:
        chosen = mem[:1]

    cited_memories: List[CitedMemory] = []
    for m in chosen:
        cited_memories.append(
            CitedMemory(
                idx=int(m.get("idx", 0)),
                conv_title=str(m.get("conv_title", "")),
                conv_id=str(m.get("conv_id", "")),
                time_range=_safe_time_range(m.get("time_range")),
                msg_ids=list(m.get("msg_ids") or []),
                score=float(m.get("score", 0.0)),
                confidence=str(m.get("confidence", "")),
                snippet=str(m.get("snippet", "")),
            )
        )

    # 4) timing（如果 agent 给了就用 agent 的；否则给 total）
    timing = _timing_from_result(res)
    if not timing:
        timing = {"total": int((t1 - t0) * 1000)}

    return ChatResp(answer=answer_text, cited_memories=cited_memories, timing_ms=timing)


