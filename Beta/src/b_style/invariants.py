from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple
import re

# 数字（含百分比、小数）
RE_NUMBER = re.compile(r"(?<![\w.])\d+(?:\.\d+)?%?(?![\w.])")

# 日期/时间（beta 粗规则：够用）
RE_DATE = re.compile(
    r"\b("
    r"\d{4}[-/]\d{1,2}[-/]\d{1,2}"      # 2026-02-20
    r"|"
    r"\d{1,2}月\d{1,2}日"               # 2月20日
    r"|"
    r"\d{1,2}[:：]\d{2}"                # 15:30
    r")\b"
)

# 承诺/动作词（可按业务继续扩）
COMMITMENT_KEYWORDS = [
    "我会", "我今天", "我明天", "我这周", "我下周",
    "发你", "更新", "确认", "回签", "交付", "上线",
    "部署", "培训", "付款", "签约", "发版", "对齐"
]


@dataclass
class InvariantViolation:
    kind: str        # numbers | dates | commitments
    detail: str


def _extract_numbers(s: str) -> List[str]:
    return RE_NUMBER.findall(s or "")


def _extract_dates(s: str) -> List[str]:
    return RE_DATE.findall(s or "")


def _extract_commitment_hits(s: str) -> List[str]:
    s = s or ""
    return [k for k in COMMITMENT_KEYWORDS if k in s]


def check_invariants(
    original: str,
    rewritten: str,
    preserve_numbers: bool = True,
    preserve_dates: bool = True,
    preserve_commitments: bool = True,
) -> Tuple[bool, List[InvariantViolation]]:
    """
    硬校验：不允许丢失/改写关键事实信号。
    beta 规则：
      - original 中出现的数字/日期/承诺提示词，rewritten 里必须也出现
    """
    violations: List[InvariantViolation] = []

    if preserve_numbers:
        o = _extract_numbers(original)
        r = _extract_numbers(rewritten)
        missing = [x for x in o if x not in r]
        if missing:
            violations.append(InvariantViolation("numbers", f"missing numbers: {missing}"))

    if preserve_dates:
        o = _extract_dates(original)
        r = _extract_dates(rewritten)
        missing = [x for x in o if x not in r]
        if missing:
            violations.append(InvariantViolation("dates", f"missing dates/times: {missing}"))

    if preserve_commitments:
        o = _extract_commitment_hits(original)
        r = _extract_commitment_hits(rewritten)
        missing = [x for x in o if x not in r]
        if missing:
            violations.append(InvariantViolation("commitments", f"missing commitment cues: {missing}"))

    return (len(violations) == 0), violations