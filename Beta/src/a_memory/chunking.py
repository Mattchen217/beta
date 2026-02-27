from dataclasses import dataclass
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from dateutil.parser import isoparse
import re

from src.a_memory.config import MIN_TEXT_LEN, MAX_CHUNK_CHARS
from src.a_memory.preprocess import normalize_text

# “纯寒暄/确认”噪声词：只在信息量极低时丢弃
NOISE_WORDS = {"嗯", "好的", "哈哈", "ok", "OK", "好", "收到", "行", "可以", "没问题", "thanks", "thx"}

# 短文本但信息密度高：保留（金额/数字/日期/关键符号）
INFO_DENSE_RE = (
    r"(\d{1,4}(\.\d+)?\s*(万|w|k|K|元|块|美元|\$|¥))"  # 金额/数量
    r"|(\d{4}[-/]\d{1,2}[-/]\d{1,2})"                 # 日期
    r"|(\d{1,2}:\d{2})"                               # 时间
    r"|(#\w+|@\w+)"                                   # 话题/提及
)

@dataclass
class Chunk:
    chunk_id: str
    conv_id: str
    time_start: str
    time_end: str
    text: str
    message_ids: List[str]
    # 可选：用于更强的可解释性（beta 可以不入库）
    senders: Optional[List[str]] = None

def _is_punct_only(t: str) -> bool:
    return all(ch in "😂🤣….,!?，。！？" for ch in t)

def is_noise(text: str) -> bool:
    """
    噪声判定原则：
    - 允许短，但不能“无信息”
    - 如果包含数字/金额/日期等信息，哪怕很短也保留
    """
    t = normalize_text(text)
    if not t:
        return True
    if _is_punct_only(t):
        return True
    if re.search(INFO_DENSE_RE, t):
        return False
    # 低于阈值且属于寒暄词，丢弃
    if len(t) < MIN_TEXT_LEN and t in NOISE_WORDS:
        return True
    # 低于阈值但不是寒暄词：保留（例如“20万”/“发了”/“签了”）
    if len(t) < MIN_TEXT_LEN:
        return False
    # 长文本但只有寒暄
    if t in NOISE_WORDS:
        return True
    return False

import re

def build_chunks(
    conv_id: str,
    messages: List[Dict],
    *,
    max_messages: int = 8,
    min_messages: int = 2,
    time_gap_minutes: int = 30,
) -> List[Chunk]:
    """
    Beta 版 chunking：
    - 以“时间间隔 + 消息上限”切分（比固定 3 条稳定很多）
    - 保证 chunk 不截断在消息中间（不做字符硬截断；必要时拆成多个 chunk）
    - 保留短但信息密度高的文本（修复 MIN_TEXT_LEN 误杀）
    """
    chunks: List[Chunk] = []
    buf = []  # (id, sender, ts, text)
    start_ts = None
    last_kept_ts = None

    def flush(end_ts: str):
        nonlocal buf, start_ts, last_kept_ts
        if not buf:
            return

        # 组装文本：带 sender 标签，但尽量简洁
        lines = [f'{sender}: {txt}' for (_id, sender, _ts, txt) in buf]
        text_all = "\n".join(lines)

        # 如超过 MAX_CHUNK_CHARS，则按消息边界拆分
        cur_lines, cur_ids, cur_senders = [], [], []
        cur_start = buf[0][2]
        cur_len = 0

        def emit(cur_end: str):
            if not cur_ids:
                return
            chunk_id = f"{conv_id}_{cur_ids[0]}_{cur_ids[-1]}"
            chunks.append(Chunk(
                chunk_id=chunk_id,
                conv_id=conv_id,
                time_start=cur_start,
                time_end=cur_end,
                text="\n".join(cur_lines),
                message_ids=list(cur_ids),
                senders=list(cur_senders),
            ))

        for (_id, sender, ts, txt) in buf:
            line = f"{sender}: {txt}"
            # +1 是换行
            added = len(line) + (1 if cur_lines else 0)
            if cur_lines and (cur_len + added) > MAX_CHUNK_CHARS:
                emit(prev_ts)
                # reset
                cur_lines, cur_ids, cur_senders = [], [], []
                cur_start = ts
                cur_len = 0

            cur_lines.append(line)
            cur_ids.append(_id)
            cur_senders.append(sender)
            cur_len += added
            prev_ts = ts

        # emit tail
        emit(buf[-1][2])

        # reset buffer
        buf = []
        start_ts = None
        last_kept_ts = None

    gap = timedelta(minutes=time_gap_minutes)

    for m in messages:
        raw = m.get("text", "")
        txt = normalize_text(raw)
        if is_noise(txt):
            continue

        ts = m["ts"]
        if start_ts is None:
            start_ts = ts

        # 时间间隔切分（与上一条保留消息比较）
        if last_kept_ts is not None:
            if isoparse(ts) - isoparse(last_kept_ts) > gap and len(buf) >= 1:
                flush(last_kept_ts)

        buf.append((m["id"], m["sender"], ts, txt))
        last_kept_ts = ts

        # 消息上限切分
        if len(buf) >= max_messages:
            flush(ts)

    # 收尾：至少 min_messages 才单独成块，否则并入上一块（beta 简化：直接 flush）
    if buf:
        flush(last_kept_ts or messages[-1]["ts"])

    # 合并过碎的 chunk（<min_messages）到前一个：避免碎片影响检索
    merged: List[Chunk] = []
    for c in chunks:
        if merged and len(c.message_ids) < min_messages:
            prev = merged[-1]
            prev.text = prev.text + "\n" + c.text
            prev.time_end = c.time_end
            prev.message_ids.extend(c.message_ids)
            if prev.senders and c.senders:
                prev.senders.extend(c.senders)
        else:
            merged.append(c)

    return merged
