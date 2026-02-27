from dataclasses import dataclass
from typing import List, Dict, Any
import difflib

from .rules import RuleEdit


@dataclass
class DiffReport:
    rule_edits: List[RuleEdit]
    summary: str
    char_diff_ratio: float
    added_lines: List[str]
    removed_lines: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.summary,
            "char_diff_ratio": self.char_diff_ratio,
            "rule_edits": [e.__dict__ for e in self.rule_edits],
            "added_lines": self.added_lines,
            "removed_lines": self.removed_lines,
        }


def build_diff_report(before: str, after: str, rule_edits: List[RuleEdit]) -> DiffReport:
    sm = difflib.SequenceMatcher(a=before, b=after)
    ratio = 1.0 - sm.ratio()

    b_lines = [x.strip() for x in (before or "").splitlines() if x.strip()]
    a_lines = [x.strip() for x in (after or "").splitlines() if x.strip()]

    added = [x for x in a_lines if x not in b_lines]
    removed = [x for x in b_lines if x not in a_lines]

    summary = f"edits={len(rule_edits)} | changed≈{ratio:.2f}"

    return DiffReport(
        rule_edits=rule_edits,
        summary=summary,
        char_diff_ratio=ratio,
        added_lines=added[:10],
        removed_lines=removed[:10],
    )