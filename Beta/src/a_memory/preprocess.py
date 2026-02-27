# src/preprocess.py
import re
import unicodedata

URL_RE = re.compile(r"(https?://\S+|www\.\S+)", re.I)
WS_RE = re.compile(r"\s+")
PUNCT_REPEAT_RE = re.compile(r"([!?！？。,.，…])\1{2,}")

def normalize_text(text: str) -> str:
    """
    轻量清洗：不改变语义，只提升检索/切分稳定性。
    - Unicode 规范化
    - 统一空白
    - 压缩重复标点
    - 去掉明显无用的零宽字符
    """
    if text is None:
        return ""
    t = unicodedata.normalize("NFKC", str(text))
    # 去零宽
    t = t.replace("\u200b", "").replace("\ufeff", "")
    # 统一换行/空白
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    t = WS_RE.sub(" ", t).strip()
    # 压缩重复标点（保留情绪但别无限长）
    t = PUNCT_REPEAT_RE.sub(r"\1\1", t)
    return t

def light_mask_pii(text: str) -> str:
    """
    可选：本地存储也建议做“展示层脱敏”，不改原始库也行。
    """
    t = text
    t = re.sub(r"\b1[3-9]\d{9}\b", "[PHONE]", t)           # CN phone
    t = re.sub(r"\b\d{3}[- ]?\d{3}[- ]?\d{4}\b", "[PHONE]", t)  # US phone
    t = re.sub(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "[EMAIL]", t)
    return t


def tokenize_for_bm25(text: str):
    """
    BM25 用的 tokenizer：
    - 有 jieba 就用 jieba（中文）
    - 否则：中文按 2-gram + 英文/数字按词
    """
    t = normalize_text(text)
    try:
        import jieba  # type: ignore
        toks = [w.strip() for w in jieba.lcut(t) if w.strip()]
        return toks if toks else list(t)
    except Exception:
        # fallback: 中英文混合
        zh = re.findall(r"[\u4e00-\u9fff]+", t)
        en = re.findall(r"[A-Za-z0-9_]+", t)
        toks = []
        for block in zh:
            if len(block) == 1:
                toks.append(block)
            else:
                # 2-gram
                toks.extend([block[i:i+2] for i in range(len(block)-1)])
        toks.extend([w.lower() for w in en])
        return toks if toks else list(t)
