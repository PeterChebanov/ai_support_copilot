"""Input guard for /ask and /retrieve — FastAPI dependency helpers."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi.responses import JSONResponse

from security.injection import (
    MAX_QUERY_LENGTH,
    detect_injection,
    exceeds_max_length,
)


@dataclass(frozen=True)
class GuardResult:
    allowed: bool
    reason: str | None = None
    pattern_name: str | None = None


def check_input(text: str, *, max_length: int = MAX_QUERY_LENGTH) -> GuardResult:
    """Validate user text before retrieval / generation."""
    if exceeds_max_length(text, max_length=max_length):
        return GuardResult(allowed=False, reason="query_too_long")

    hit = detect_injection(text)
    if hit.matched:
        return GuardResult(
            allowed=False,
            reason=hit.reason or "injection_detected",
            pattern_name=hit.pattern_name,
        )
    return GuardResult(allowed=True)


def blocked_response(result: GuardResult) -> JSONResponse:
    """HTTP 400 body matching the course demo contract."""
    body: dict[str, str] = {
        "error": "blocked",
        "reason": result.reason or "injection_detected",
    }
    if result.pattern_name:
        body["pattern"] = result.pattern_name
    return JSONResponse(status_code=400, content=body)


def enforce_or_block(text: str) -> JSONResponse | None:
    """Return a 400 JSONResponse when blocked; otherwise None."""
    result = check_input(text)
    if result.allowed:
        return None
    return blocked_response(result)
