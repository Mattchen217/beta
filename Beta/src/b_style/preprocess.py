import re

_ZERO_WIDTH = re.compile(r"[\u200b\u200c\u200d\ufeff]")
_MULTI_SPACE = re.compile(r"[ \t]+")
_MULTI_NL = re.compile(r"\n{3,}")


def normalize_text(s: str) -> str:
    if not s:
        return ""
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = _ZERO_WIDTH.sub("", s)
    s = "\n".join(line.rstrip() for line in s.split("\n"))
    s = _MULTI_SPACE.sub(" ", s)
    s = _MULTI_NL.sub("\n\n", s)
    return s.strip()