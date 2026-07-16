# AI Support Copilot — Case Study

## What we built

Cycle 1 delivers a local, production-shaped support assistant:

- ingest markdown/text documents into PostgreSQL + pgvector
- hybrid retrieval (Postgres FTS + vector -> RRF -> rerank)
- grounded `/ask` answers with validated citations
- Redis exact + semantic cache
- RAGAS baseline and regression gates
- prompt-injection defense and role-based ACL

The stack is intentionally local-first: Docker Compose, FastAPI, Postgres, Redis, OpenAI, pytest, GitHub Actions.

## Business case

Support work is repetitive, policy-heavy, and citation-friendly. That makes it a strong fit for deterministic RAG before more agentic behavior:

- manual support handling: roughly `$4-8` per ticket
- AI-assisted handling: roughly `$0.30-0.80` per ticket
- Klarna publicly reported large savings from support automation, which motivates the app shape even if this repo stays local-first

## Why pipeline, not agent

This app deliberately chooses a pipeline:

1. ingest
2. retrieve
3. generate
4. cache
5. evaluate
6. secure

That is enough for support Q&A because:

- the task is mostly single-turn
- the information source is a bounded knowledge base
- correctness and traceability matter more than open-ended tool use
- citations and regression tests are easier to reason about in a deterministic flow

An agent loop would add complexity earlier than it adds value here.

## Key decisions

### Retrieval

- **Keyword + vector** beats pure vector for policy/support language
- **RRF** merges sparse and dense retrieval without forcing score normalization
- **Lightweight rerank** is a good latency/complexity trade-off for cycle 1

### Generation

- output is structured JSON
- every factual answer must carry citations
- citations are validated against retrieved chunk text, not trusted blindly

### Caching

- exact cache removes repeated identical asks
- semantic cache removes paraphrase cost
- cache keys are role-scoped after EP10 to avoid cross-role leaks

### Quality

- curated golden set with factual, policy, and negative questions
- committed baseline scorecard
- offline regression gate in CI using thresholds, not live LLM calls

### Security

- direct injection blocked before the model sees the query
- XML delimiters and prompt hierarchy harden the generation prompt
- ACL blocks restricted chunks at retrieval time

## What we learned

- evaluation and security deserve their own episodes; they are not “afterthought polish”
- cache design is part of security, not just performance
- grounded generation without citation validation is still too trusting
- a small, well-curated golden dataset is enough to make quality visible
- for this workload, simplicity compounds: Postgres + pgvector + Redis + FastAPI is enough

## What is intentionally out of scope

- cloud deployment / Kubernetes
- multi-tenant auth system
- external vector database
- agent loops / tool orchestration
- large-scale observability platform

## Final repo value

The repo works as:

- a compact RAG reference implementation
- a teaching project with episode-by-episode checkpoints
- a portfolio case study showing product, quality, and security thinking together
