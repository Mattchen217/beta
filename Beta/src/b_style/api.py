from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any, List

from .style_profile import StyleProfile
from .preprocess import normalize_text
from .rules import rule_rewrite, RuleEdit
from .invariants import check_invariants, InvariantViolation
from .diff_report import build_diff_report, DiffReport
from .gating import should_apply_style
from .adapter.apply import StyleAdapter


@dataclass
class StyleRewriteResult:
    styled_reply: str
    applied: bool
    ok_invariants: bool
    violations: List[InvariantViolation]
    diff: DiffReport
    meta: Dict[str, Any]


def style_rewrite(
    draft_reply: str,
    profile: StyleProfile,
    intent: Optional[str] = None,
    adapter: Optional[StyleAdapter] = None,
    force: bool = False,
) -> StyleRewriteResult:
    draft_reply = draft_reply or ""
    applied = should_apply_style(intent, force=force)

    before = normalize_text(draft_reply)

    if not applied:
        diff = build_diff_report(before, before, [])
        return StyleRewriteResult(
            styled_reply=before,
            applied=False,
            ok_invariants=True,
            violations=[],
            diff=diff,
            meta={"intent": intent, "forced": force, "adapter": False},
        )

    # 1) Rule Rewrite（强约束）
    ruled, edits = rule_rewrite(before, profile)

    # 2) Adapter Rewrite（LoRA 可选）
    adapter_used = False
    after = ruled
    if adapter is not None and getattr(adapter, "enabled", False):
        adapter_used = True
        after = adapter.rewrite(ruled, profile)

    after = normalize_text(after)

    # 3) Invariant Check（硬校验）
    ok, violations = check_invariants(
        original=before,
        rewritten=after,
        preserve_numbers=profile.safety.must_preserve_numbers,
        preserve_dates=profile.safety.must_preserve_dates,
        preserve_commitments=profile.safety.must_preserve_commitments,
    )

    # 4) 失败回滚（极保守：回到 rule-only；若你更保守可回到 original）
    if not ok:
        after = normalize_text(ruled)
        edits = edits + [RuleEdit(kind="invariant_fail", before="lora_output", after="rule_only", note=str([v.detail for v in violations]))]
        ok2, violations2 = check_invariants(
            original=before,
            rewritten=after,
            preserve_numbers=profile.safety.must_preserve_numbers,
            preserve_dates=profile.safety.must_preserve_dates,
            preserve_commitments=profile.safety.must_preserve_commitments,
        )
        # rule-only 理论上应当更安全；如果仍 fail，回到 original
        if not ok2:
            after = before
            edits.append(RuleEdit(kind="invariant_fail", before="rule_only", after="original", note="reverted to original"))
            ok, violations = False, violations2
        else:
            ok, violations = True, []

    # 5) Diff Report（可解释）
    diff = build_diff_report(before, after, edits)

    return StyleRewriteResult(
        styled_reply=after,
        applied=True,
        ok_invariants=ok,
        violations=violations,
        diff=diff,
        meta={"intent": intent, "forced": force, "adapter": adapter_used},
    )