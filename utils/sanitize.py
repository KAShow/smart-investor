"""Input sanitization to defend against prompt injection."""
import re

# Patterns commonly used in prompt-injection attempts.
_INJECTION_PATTERNS = [
    r'ignore\s+(?:all\s+)?previous\s+(?:instructions|prompts)',
    r'disregard\s+(?:all\s+)?(?:previous|above)',
    r'forget\s+(?:everything|previous)',
    r'system\s*[:：]',
    r'assistant\s*[:：]',
    r'<\|im_(?:start|end)\|>',
    r'\[INST\]',
    r'\[/INST\]',
    r'</?(?:system|assistant|user)\b[^>]*>',
    r'تجاهل\s+(?:جميع\s+|كل\s+)?(?:التعليمات|الأوامر)\s*(?:السابقة|أعلاه)?',
    r'انس\s+(?:جميع\s+|كل\s+)?(?:التعليمات|ما\s+قيل)\s*(?:السابقة|أعلاه)?',
    r'تعليمات\s+جديدة\s*[:：]',
    r'دور\s+جديد\s*[:：]',
]

_INJECTION_REGEX = re.compile('|'.join(_INJECTION_PATTERNS), re.IGNORECASE | re.UNICODE)


def sanitize_user_input(text: str | None, max_len: int = 2000) -> str:
    """Defang likely prompt-injection patterns and clamp length.

    Returns an empty string for None / non-string. Replaces matched patterns with
    '[محذوف]' so the AI sees that content was filtered without us silently dropping it.
    """
    if not text or not isinstance(text, str):
        return ''
    cleaned = text.strip()[:max_len]
    cleaned = _INJECTION_REGEX.sub('[محذوف]', cleaned)
    cleaned = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', cleaned)
    return cleaned


def sanitize_for_log(text: str | None, max_len: int = 200) -> str:
    """Make a string safe for log lines: strip newlines, clamp length."""
    if not text:
        return ''
    return re.sub(r'\s+', ' ', str(text))[:max_len]
