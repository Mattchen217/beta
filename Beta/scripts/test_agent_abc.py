from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

from src.b_style.style_profile import StyleProfile
from src.b_style.adapter.apply import StyleAdapter, LoraAdapterConfig
from src.copilot.agent_abc import CopilotAgentABC


def try_load_adapter(project_root: Path):
    adapter_path = project_root / "data" / "style_adapters" / "user_default" / "v1"
    if not adapter_path.exists():
        return None
    try:
        return StyleAdapter(
            LoraAdapterConfig(
                base_model_name_or_path="google/gemma-3-1b-it",
                adapter_path=str(adapter_path),
                dtype="bfloat16",
            )
        )
    except Exception as e:
        print("⚠️  LoRA adapter 加载失败，将只用 rule-only：", e)
        return None


# ---------- console UI helpers ----------
def _truncate(s: str, n: int) -> str:
    s = (s or "").replace("\r\n", "\n").replace("\r", "\n")
    if len(s) <= n:
        return s
    return s[: max(0, n - 1)] + "…"


def _box(title: str, lines: List[str], width: int = 88) -> str:
    # safe width
    width = max(width, 60)
    top = f"┌{'─' * (width - 2)}┐"
    ttl = f"│ {title}".ljust(width - 1) + "│"
    sep = f"├{'─' * (width - 2)}┤"
    body = []
    for ln in lines:
        for sub in (ln or "").split("\n"):
            body.append(("│ " + sub)[: width - 1].ljust(width - 1) + "│")
    bot = f"└{'─' * (width - 2)}┘"
    return "\n".join([top, ttl, sep, *body, bot])


def _pill(label: str, value: Any) -> str:
    return f"[{label}: {value}]"


def _render_timing(style_trace: Dict[str, Any]) -> str:
    t = (style_trace.get("meta") or {}).get("timing_ms") or {}
    if not t:
        return ""
    parts = [
        _pill("A检索", f"{t.get('A_retrieval', 0)}ms"),
        _pill("B回答", f"{t.get('B_answer', 0)}ms"),
        _pill("C风格", f"{t.get('C_style', 0)}ms"),
        _pill("总耗时", f"{t.get('total', 0)}ms"),
    ]
    return " ".join(parts)


def _parse_answer_evidence(raw_answer: str) -> Tuple[str, List[str]]:
    """
    Parse the B output format:
      Answer: ...
      Evidence:
      - [1] ...
      - [2] ...
    """
    raw = (raw_answer or "").strip().replace("\r\n", "\n")
    ans = raw
    ev_lines: List[str] = []
    if "Answer:" in raw and "\nEvidence:" in raw:
        a, rest = raw.split("\nEvidence:", 1)
        ans = a.replace("Answer:", "", 1).strip()
        for ln in rest.splitlines():
            ln = ln.strip()
            if ln.startswith("-"):
                ev_lines.append(ln[1:].strip())
    return ans, ev_lines


def main():
    project_root = Path(__file__).resolve().parents[1]

    profile = StyleProfile()
    adapter = try_load_adapter(project_root)

    agent = CopilotAgentABC(profile=profile, adapter=adapter)

    print(_box("HetaiAI Beta (ABC) — Demo Console", [
        "A: 记忆检索（向量 + BM25）",
        "B: 证据驱动回答（Answer + Evidence）",
        "C: 可选风格润色（仅对外回复启用）",
        "",
        "输入 q 退出。"
    ], width=88))
    print()

    while True:
        q = input("🟦 问题 > ").strip()
        if not q:
            continue
        if q.lower() == "q":
            break

        m = input("🟨 模式（1=自己问自己, 2=对外回复）> ").strip()
        mode = "external_reply" if m == "2" else "self_qa"

        res = agent.answer(q, top_k=5, mode=mode)

        timing_line = _render_timing(res.style_trace)
        applied = "✅ 已启用" if res.style_trace.get("meta", {}).get("adapter") else "⛔ 未启用"
        mode_label = "对外回复" if mode == "external_reply" else "自己问自己"

        header = f"{_pill('模式', mode_label)} {_pill('风格', applied)}"
        if timing_line:
            header += "  " + timing_line

        print()
        print(_box("RESULT", [header], width=88))
        print()

        # FINAL answer (prefer styled)
        final_ans, final_ev = _parse_answer_evidence(res.final_answer)
        print(_box("FINAL ANSWER", [final_ans], width=88))
        if final_ev:
            print(_box("EVIDENCE (selected)", [f"{i+1}. {final_ev[i]}" for i in range(min(4, len(final_ev)))], width=88))
        print()

        # RAW (only external reply shows)
        if res.style_trace.get("meta", {}).get("mode") == "external_reply":
            raw_ans, raw_ev = _parse_answer_evidence(res.raw_answer)
            print(_box("RAW (before style)", [raw_ans], width=88))
            if raw_ev:
                print(_box("RAW EVIDENCE (selected)", [f"{i+1}. {raw_ev[i]}" for i in range(min(4, len(raw_ev)))], width=88))
            print()

        # MEMORY TRACE (top 3) compact
        trace_lines: List[str] = []
        for mm in res.memory_trace[:3]:
            tr = mm.get("time_range") or ("", "")
            trace_lines.append(
                f"[{mm['idx']}] {mm['conv_title'] or '（无标题）'}  score={mm['score']:.3f}  msg_ids={','.join(mm['msg_ids']) or '—'}"
            )
            if tr[0] or tr[1]:
                trace_lines.append(f"     time: {tr[0]} ~ {tr[1]}")
            trace_lines.append(f"     snippet: {_truncate(mm.get('snippet', ''), 180)}")
            trace_lines.append("")

        print(_box("MEMORY TRACE (top 3)", trace_lines[:-1] if trace_lines else ["（无）"], width=88))
        print()


if __name__ == "__main__":
    main()
