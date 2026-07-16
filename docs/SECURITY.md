# Security notes — Cycle 1

## OWASP LLM01 — Prompt Injection

This app mitigates **direct** prompt injection on user queries:

| Control | Where |
|---------|--------|
| Pattern denylist + max query length | `security/injection.py` |
| Guard before cache / retrieve / generate | `security/guard.py` on `/ask` and `/retrieve` |
| Prompt hierarchy + XML delimiters | `generation/prompt.py` |

Blocked requests return HTTP **400**:

```json
{"error": "blocked", "reason": "injection_detected"}
```

**Indirect** injection (malicious text inside retrieved chunks) is out of scope for cycle-1 pattern filters; grounding + citation validation reduce impact. ACL (EP10) addresses data leakage separately.
