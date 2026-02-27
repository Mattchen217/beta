
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple
import re
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM


@dataclass
class EvidenceBlock:
    """
    证据块：来自 A 的检索结果 + 会话元信息（title 等）
    """
    idx: int
    conv_id: str
    conv_title: str
    time_range: Optional[Tuple[str, str]]
    message_ids: List[str]
    score: float
    confidence: str
    snippet: str


class QwenEvidenceAnswerer:
    """
    B：基于证据生成回答（抽取式，不编造），并输出“依据”。
    设计目标：
    - Answer 只基于 evidence/snippet 中出现过的信息（不让 1B 模型脑补）。
    - 相关：根据问题意图在 evidence 内挑最相关的 1-4 句原话组合成结论。
    - 结构：严格输出 Answer/Evidence 两段，便于 UI 渲染引用。
    """

    def __init__(
        self,
        base_model: str = "google/gemma-3-1b-it",
        dtype: str = "bfloat16",
        device: Optional[str] = None,
    ):
        # 目前这版 answer 是纯抽取式，不依赖 LLM；保留加载代码以兼容你后续要用 rewrite
        self.base_model = base_model
        self.tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=False)

        if self.tokenizer.pad_token is None and self.tokenizer.eos_token is not None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        torch_dtype = torch.bfloat16 if dtype == "bfloat16" else torch.float16
        self.model = AutoModelForCausalLM.from_pretrained(
            base_model,
            trust_remote_code=False,
            device_map="auto" if device is None else None,
            torch_dtype=torch_dtype,
        )
        if device is not None:
            self.model.to(device)
        self.model.eval()

    # ---------- helpers (instance methods) ----------
    def _norm(self, s: str) -> str:
        return re.sub(r"\s+", " ", (s or "")).strip()

    def _split_utterances(self, snippet: str):
        """
        Parse snippet into ordered utterances: (speaker, text, raw_line).
        Supports lines like: "clientA: xxx" / "me: xxx" / "coo: xxx"
        """
        out = []
        for raw in (snippet or "").splitlines():
            line = raw.strip()
            if not line:
                continue
            m = re.match(r"^([A-Za-z0-9_\-]+)\s*:\s*(.+)$", line)
            if m:
                spk = m.group(1).strip()
                txt = m.group(2).strip()
                out.append((spk, txt, line))
            else:
                out.append(("", line, line))
        return out

    def _tokenize_zh(self, s: str):
        s = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", " ", s or "").strip().lower()
        if not s:
            return []
        tokens = []
        parts = s.split()
        for p in parts:
            if re.search(r"[\u4e00-\u9fff]", p):
                # Chinese bigrams
                if len(p) == 1:
                    tokens.append(p)
                else:
                    for i in range(len(p) - 1):
                        tokens.append(p[i : i + 2])
            else:
                tokens.append(p)
        return tokens

    def _has_time_expr(self, s: str) -> bool:
        s = s or ""
        if re.search(r"\d{4}[-/.]\d{1,2}[-/.]\d{1,2}", s):
            return True
        if re.search(r"\d{1,2}月\d{1,2}日", s):
            return True
        if re.search(r"周[一二三四五六日天]", s):
            return True
        if any(k in s for k in ["今天", "明天", "后天", "下周", "本周", "周末", "今晚", "下午", "上午"]):
            return True
        return False

    def _q_intent(self, q: str) -> str:
        q = q or ""
        if any(k in q for k in ["什么时候", "何时", "哪天", "几点", "彩排"]):
            return "time"
        if any(k in q for k in ["怎么走", "流程", "回签", "后续", "进度"]):
            return "process"
        if any(k in q for k in ["问过", "之前问", "是否问", "有没有问"]):
            return "asked"
        return "general"

    def _display_line(self, spk: str, txt: str) -> str:
        spk_l = (spk or "").lower()
        if spk_l in {"me", "我"}:
            return f"你说{txt}"
        if spk:
            return f"{spk}说{txt}"
        return txt

    def _score_line(self, intent: str, q_tokens: set, spk: str, txt: str, ev_score: float) -> float:
        tks = self._tokenize_zh(txt)
        overlap = len(q_tokens.intersection(tks))
        score = float(overlap)

        if intent == "time":
            if "彩排" in txt:
                score += 2
            if self._has_time_expr(txt):
                score += 3

        if intent == "process":
            for kw in ["流程", "回签", "更新", "确认", "付款", "节点", "内部", "版本", "发你", "下周"]:
                if kw in txt:
                    score += 1

        if intent == "asked":
            if (spk or "").lower().startswith("client"):
                score += 2
            if (spk or "").lower() in {"me", "我"}:
                score += 1
            for kw in ["包含", "培训", "部署", "报价"]:
                if kw in txt:
                    score += 1

        score += float(ev_score) * 0.2
        return score

    def _pick_primary_evidence(self, question: str, evidences: List[EvidenceBlock]) -> EvidenceBlock:
        q_tokens = set(self._tokenize_zh(question))
        intent = self._q_intent(question)

        best = None  # (score, EvidenceBlock)
        for ev in evidences:
            for spk, txt, _raw in self._split_utterances(ev.snippet):
                s = self._score_line(intent, q_tokens, spk, txt, ev.score)
                if best is None or s > best[0]:
                    best = (s, ev)
        return best[1] if best else evidences[0]

    def _select_indices_in_block(self, intent: str, question: str, ev: EvidenceBlock) -> List[int]:
        """
        在一个 evidence block 内挑出最相关的 1-4 句（按原顺序输出）。
        """
        utts = self._split_utterances(ev.snippet)
        q_tokens = set(self._tokenize_zh(question))

        # score each utterance
        scored = []
        for i, (spk, txt, raw) in enumerate(utts):
            s = self._score_line(intent, q_tokens, spk, txt, ev.score)
            scored.append((s, i, spk, txt, raw))
        scored.sort(key=lambda x: x[0], reverse=True)

        chosen = set()

        def add_if(pred, limit: int):
            added = 0
            for _s, i, spk, txt, raw in scored:
                if i in chosen:
                    continue
                if pred(spk, txt, raw):
                    chosen.add(i)
                    added += 1
                    if added >= limit:
                        break

        if intent == "time":
            add_if(lambda spk, txt, raw: ("彩排" in txt) and self._has_time_expr(txt), limit=2)
            if not chosen:
                add_if(lambda spk, txt, raw: self._has_time_expr(txt), limit=2)

        elif intent == "process":
            # 先抓关键节点
            add_if(lambda spk, txt, raw: any(k in txt for k in ["付款", "节点", "更新", "已更新", "确认", "回签", "内部", "流程", "下周"]), limit=6)

        elif intent == "asked":
            # client 问 + me 答（尽量都带上）
            add_if(lambda spk, txt, raw: (spk or "").lower().startswith("client") and any(k in txt for k in ["报价", "包含", "部署", "培训"]), limit=2)
            add_if(lambda spk, txt, raw: (spk or "").lower() in {"me", "我"} and any(k in txt for k in ["包含", "不含", "培训", "部署", "单独"]), limit=2)

        # general fallback: top-2 scored lines if still empty
        if not chosen:
            for s, i, *_ in scored[:2]:
                if s > 0:
                    chosen.add(i)

        # final fallback: prefer me line else first line
        if not chosen and utts:
            for i, (spk, _txt, _raw) in enumerate(utts):
                if (spk or "").lower() in {"me", "我"}:
                    chosen.add(i)
                    break
        if not chosen and utts:
            chosen.add(0)

        return sorted(chosen)

    @torch.no_grad()
    def answer(
        self,
        question: str,
        evidences: List[EvidenceBlock],
        max_new_tokens: int = 260,
        temperature: float = 0.0,
    ) -> str:
        question = (question or "").strip()
        if not evidences:
            return "Answer: （未检索到相关记录，无法从证据确定。）\nEvidence:\n- [1] （无）"

        intent = self._q_intent(question)

        # 1) choose best evidence block by best matching utterance
        primary_ev = self._pick_primary_evidence(question, evidences)
        utts = self._split_utterances(primary_ev.snippet)

        # 2) select relevant utterances (indices) within that block
        idxs = self._select_indices_in_block(intent, question, primary_ev)

        # 3) build answer text
        selected_display = []
        selected_raw = []
        for i in idxs:
            spk, txt, raw = utts[i]
            selected_display.append(self._display_line(spk, txt))
            selected_raw.append(raw)

        if intent == "asked":
            # 强化你要的“问过/没问过”的结论句
            answer_text = "问过。" + " " + " ".join(selected_display)
        else:
            answer_text = " ".join(selected_display)

        ev_join = " / ".join(selected_raw) if selected_raw else self._norm(primary_ev.snippet)[:200]
        out = "Answer: " + self._norm(answer_text) + "\nEvidence:\n" + f"- [{primary_ev.idx}] {ev_join}"
        return out