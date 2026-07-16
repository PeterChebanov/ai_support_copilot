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

## ACL and data leakage (EP10)

This app filters retrieval results by role metadata before reranking and generation:

| Control | Where |
|---------|--------|
| `allowed_roles` stored in chunk metadata | `ingestion/chunker.py` / `ingestion/store.py` |
| Query-time ACL filter | `retrieval/acl.py` and `retrieval/pipeline.py` |
| API role input | `api/models.py`, `/ask`, `/retrieve` |
| Role-scoped cache keys | `cache/exact.py`, `cache/semantic.py`, `cache/middleware.py` |

Default roles:

- `faq.md`, `policies.md` -> `["support", "admin"]`
- `internal-admin.md` -> `["admin"]`

This prevents both direct retrieval leakage and cross-role cache leakage.
