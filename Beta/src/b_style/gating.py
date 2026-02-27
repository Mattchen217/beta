from typing import Optional

ENABLE_INTENTS = {
    "draft_reply_with_memory",
    "rewrite_to_sound_like_me",
    "polish_message",
    "customer_support_reply",
    "announcement",
}

DISABLE_INTENTS = {
    "analysis",
    "math",
    "code",
    "high_stakes_legal",
    "high_stakes_medical",
}

def should_apply_style(intent: Optional[str], force: bool = False) -> bool:
    if force:
        return True
    if not intent:
        return False
    if intent in DISABLE_INTENTS:
        return False
    if intent in ENABLE_INTENTS:
        return True
    return False