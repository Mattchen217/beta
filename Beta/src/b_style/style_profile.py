from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Literal
import json

PolitenessLevel = int  # 1~5
Level = int            # 1~5

EmojiLevel = Literal["none", "low", "medium", "high"]
BulletStyle = Literal["dash", "dot", "number"]
ConfidenceStyle = Literal["calm_assertive", "soft", "strong"]
SentenceBias = Literal["short", "balanced", "long"]


@dataclass
class Tone:
    politeness_level: PolitenessLevel = 3
    directness_level: Level = 4
    warmth_level: Level = 2
    confidence_style: ConfidenceStyle = "calm_assertive"


@dataclass
class Greetings:
    enabled: bool = False
    preferred_openers: List[str] = field(default_factory=lambda: ["好", "收到", "明白", "可以", "我这边看了下"])
    avoid_openers: List[str] = field(default_factory=lambda: ["亲", "宝子", "哈喽"])


@dataclass
class SignOff:
    enabled: bool = True
    preferred_closings: List[str] = field(default_factory=lambda: ["我今天更新发你", "你先看下", "有变动我同步你"])
    avoid_closings: List[str] = field(default_factory=lambda: ["爱你", "么么哒"])


@dataclass
class Formatting:
    use_short_paragraphs: bool = True
    prefer_bullets: bool = True
    bullet_style: BulletStyle = "dash"
    emoji_level: EmojiLevel = "low"
    preferred_punctuation: List[str] = field(default_factory=lambda: ["，", "。", "："])
    avoid_patterns: List[str] = field(default_factory=lambda: ["！！！", "～～～"])


@dataclass
class Lexicon:
    preferred_phrases: List[str] = field(default_factory=lambda: ["这边", "可以的", "我建议", "我们先", "按这个走"])
    forbidden_words: List[str] = field(default_factory=lambda: ["绝对", "保证", "百分百"])
    softeners: List[str] = field(default_factory=lambda: ["可能", "建议", "倾向", "先"])


@dataclass
class Length:
    target_chars_min: int = 30
    target_chars_max: int = 220
    sentence_length_bias: SentenceBias = "short"


@dataclass
class Safety:
    must_preserve_numbers: bool = True
    must_preserve_dates: bool = True
    must_preserve_names: bool = True
    must_preserve_commitments: bool = True


@dataclass
class StyleProfile:
    version: str = "b_style_profile_v0.1"
    tone: Tone = field(default_factory=Tone)
    greetings: Greetings = field(default_factory=Greetings)
    sign_off: SignOff = field(default_factory=SignOff)
    formatting: Formatting = field(default_factory=Formatting)
    lexicon: Lexicon = field(default_factory=Lexicon)
    length: Length = field(default_factory=Length)
    safety: Safety = field(default_factory=Safety)
    extra: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        extra = d.pop("extra", {}) or {}
        d.update(extra)
        return d

    def to_json(self, ensure_ascii: bool = False, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=ensure_ascii, indent=indent)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "StyleProfile":
        known = dict(data)

        def pop_obj(key: str, cls, default):
            obj = known.pop(key, None)
            if obj is None:
                return default()
            if isinstance(obj, cls):
                return obj
            if isinstance(obj, dict):
                return cls(**obj)
            raise TypeError(f"{key} must be dict")

        return StyleProfile(
            version=known.pop("version", "b_style_profile_v0.1"),
            tone=pop_obj("tone", Tone, Tone),
            greetings=pop_obj("greetings", Greetings, Greetings),
            sign_off=pop_obj("sign_off", SignOff, SignOff),
            formatting=pop_obj("formatting", Formatting, Formatting),
            lexicon=pop_obj("lexicon", Lexicon, Lexicon),
            length=pop_obj("length", Length, Length),
            safety=pop_obj("safety", Safety, Safety),
            extra=known,
        )

    @staticmethod
    def from_json(s: str) -> "StyleProfile":
        return StyleProfile.from_dict(json.loads(s))