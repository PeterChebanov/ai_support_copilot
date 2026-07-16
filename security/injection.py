"""Direct prompt-injection pattern detection for user queries."""

from __future__ import annotations

import re
from dataclasses import dataclass

# Max characters accepted on /ask and /retrieve (DoS / dump attempts).
MAX_QUERY_LENGTH = 2000

# Case-insensitive patterns for common direct injection attempts (OWASP LLM01).
INJECTION_PATTERNS: tuple[tuple[str, str], ...] = (
    (
        r"ignore\s+(all\s+)?((previous|prior|above|earlier)\s+)?instructions?",
        "ignore_previous_instructions",
    ),
    (
        r"disregard\s+(all\s+)?(previous|prior|above)\s+(instructions?|rules?|prompts?)",
        "disregard_previous",
    ),
    (
        r"(reveal|show|print|output|display)\s+(your\s+)?(system\s+)?prompt",
        "reveal_system_prompt",
    ),
    (
        r"(reveal|show|print|output)\s+(the\s+)?(hidden\s+)?(system\s+)?instructions?",
        "reveal_instructions",
    ),
    (r"\byou\s+are\s+now\b", "role_override_you_are_now"),
    (r"\bact\s+as\s+(if\s+you\s+are|a\s+different)\b", "role_override_act_as"),
    (r"\bDAN\s+mode\b", "dan_mode"),
    (r"\bjailbreak\b", "jailbreak"),
    (
        r"\b(developer|debug)\s+mode\b.*\b(enabled|on|activated)\b",
        "developer_mode",
    ),
    (
        r"new\s+instructions?\s*:",
        "new_instructions",
    ),
)

_COMPILED = tuple(
    (re.compile(pattern, re.IGNORECASE | re.DOTALL), name)
    for pattern, name in INJECTION_PATTERNS
)


@dataclass(frozen=True)
class InjectionMatch:
    matched: bool
    pattern_name: str | None = None
    reason: str | None = None


def detect_injection(text: str) -> InjectionMatch:
    """Return whether `text` matches a known direct-injection pattern."""
    if not text or not text.strip():
        return InjectionMatch(matched=False)

    for regex, name in _COMPILED:
        if regex.search(text):
            return InjectionMatch(
                matched=True,
                pattern_name=name,
                reason="injection_detected",
            )
    return InjectionMatch(matched=False)


def exceeds_max_length(text: str, max_length: int = MAX_QUERY_LENGTH) -> bool:
    return len(text) > max_length
