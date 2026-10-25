import re


def segment(text: str, size: int, *, max_bytes: int | None = None) -> list[str]:
    """Split at sentence/word boundaries, preserving every original character."""
    if size <= 0 or (max_bytes is not None and max_bytes < 4):
        raise ValueError("Segment budget is too small")
    result = []
    while text:
        end = min(len(text), size)
        if max_bytes is not None:
            end = len(text[:end].encode("utf-8")[:max_bytes].decode("utf-8", errors="ignore"))
        if end < len(text):
            boundaries = list(re.finditer(r"(?<=[.!?])\s+|\s+", text[:end]))
            if boundaries:
                end = boundaries[-1].end()
        result.append(text[:end])
        text = text[end:]
    return result
