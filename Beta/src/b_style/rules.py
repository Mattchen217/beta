from dataclasses import dataclass
from typing import List, Tuple
import re

from .style_profile import StyleProfile


@dataclass
class RuleEdit:
    kind: str
    before: str
    after: str
    note: str = ""


def _replace_forbidden(text: str, forbidden: List[str]) -> Tuple[str, List[RuleEdit]]:
    edits: List[RuleEdit] = []
    for w in forbidden:
        if w and w in text:
            new = text.replace(w, "")
            edits.append(RuleEdit(kind="forbidden_word", before=w, after="", note="removed forbidden word"))
            text = new
    text = re.sub(r"\s{2,}", " ", text)
    text = re.sub(r"，，+", "，", text)
    text = re.sub(r"。。+", "。", text)
    return text, edits


def _normalize_punctuation(text: str, avoid_patterns: List[str]) -> Tuple[str, List[RuleEdit]]:
    edits: List[RuleEdit] = []
    for pat in avoid_patterns:
        if pat and pat in text:
            new = text.replace(pat, pat[0])
            edits.append(RuleEdit(kind="punctuation", before=pat, after=pat[0], note="collapsed repeated punctuation"))
            text = new
    new2 = re.sub(r"[!！]{2,}", "！", text)
    if new2 != text:
        edits.append(RuleEdit(kind="punctuation", before="!!", after="！", note="collapsed exclamations"))
        text = new2
    new3 = re.sub(r"[?？]{2,}", "？", text)
    if new3 != text:
        edits.append(RuleEdit(kind="punctuation", before="??", after="？", note="collapsed questions"))
        text = new3
    return text, edits


def _format_short_paragraphs(text: str) -> Tuple[str, List[RuleEdit]]:
    edits: List[RuleEdit] = []
    if "\n\n" in text:
        return text, edits
    if len(text) <= 160:
        return text, edits

    parts = re.split(r"(。|；|:|：)\s*", text)
    rebuilt = []
    buf = ""
    for i in range(0, len(parts), 2):
        seg = parts[i].strip()
        punct = parts[i + 1] if i + 1 < len(parts) else ""
        if not seg:
            continue
        buf += (seg + punct)
        if len(buf) >= 60:
            rebuilt.append(buf.strip())
            buf = ""
    if buf.strip():
        rebuilt.append(buf.strip())

    new = "\n\n".join(rebuilt).strip()
    if new != text:
        edits.append(RuleEdit(kind="formatting", before="single_paragraph", after="split_paragraphs", note="split long paragraph"))
        return new, edits
    return text, edits


def _apply_sign_off(text: str, profile: StyleProfile) -> Tuple[str, List[RuleEdit]]:
    edits: List[RuleEdit] = []
    if not profile.sign_off.enabled:
        return text, edits

    tail = text[-80:]
    if any(x in tail for x in ["谢谢", "辛苦", "我发你", "同步你", "看下", "确认", "更新"]):
        return text, edits

    closing = profile.sign_off.preferred_closings[0] if profile.sign_off.preferred_closings else ""
    if closing:
        new = text.rstrip() + "\n\n" + closing
        edits.append(RuleEdit(kind="sign_off", before="(none)", after=closing, note="added preferred closing"))
        return new, edits
    return text, edits


def _enforce_length(text: str, profile: StyleProfile) -> Tuple[str, List[RuleEdit]]:
    edits: List[RuleEdit] = []
    n = len(text)

    if n > profile.length.target_chars_max:
        before = text
        for pat in ["非常", "特别", "真的", "超级", "麻烦您", "麻烦你", "如果方便的话"]:
            text = text.replace(pat, "")
        text = re.sub(r"\s{2,}", " ", text).strip()
        if len(text) > profile.length.target_chars_max:
            text = text.replace("\n\n", "\n")
        if text != before:
            edits.append(RuleEdit(kind="length", before=f"{len(before)} chars", after=f"{len(text)} chars", note="compressed to fit length"))
        return text, edits

    if n < profile.length.target_chars_min:
        before = text
        filler = "你先看下，有需要我再补充。"
        text = (text.rstrip() + "\n\n" + filler).strip()
        edits.append(RuleEdit(kind="length", before=f"{len(before)} chars", after=f"{len(text)} chars", note="expanded with neutral action line"))
        return text, edits

    return text, edits


def rule_rewrite(text: str, profile: StyleProfile) -> Tuple[str, List[RuleEdit]]:
    edits: List[RuleEdit] = []

    text, e1 = _replace_forbidden(text, profile.lexicon.forbidden_words)
    edits += e1

    text, e2 = _normalize_punctuation(text, profile.formatting.avoid_patterns)
    edits += e2

    if profile.formatting.use_short_paragraphs:
        text, e3 = _format_short_paragraphs(text)
        edits += e3

    text, e4 = _apply_sign_off(text, profile)
    edits += e4

    text, e5 = _enforce_length(text, profile)
    edits += e5

    return text, edits