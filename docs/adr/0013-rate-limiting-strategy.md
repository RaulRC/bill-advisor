# ADR-0013: In-memory rate limiting for API endpoint

**Status:** Accepted
**Date:** 2026-06-03

## Context

The `POST /api/analyze` endpoint triggers a paid Anthropic API call (~$0.04/call). If the API is deployed publicly (Streamlit Cloud, Render, or any internet-facing host), an attacker or scraped demo could call this endpoint repeatedly and drain the API key budget.

Three approaches were considered:
1. **`slowapi`** — the standard FastAPI rate-limiting library (supports Redis, IP-based, decorator-driven)
2. **Custom ASGI middleware** — sliding-window in a Python dict, zero external deps
3. **No rate limiting** — accept the risk

## Decision

Use a custom in-memory sliding-window rate limiter implemented as FastAPI ASGI middleware (`api/rate_limiter.py`).

## Consequences

**Positive:**
- Zero additional dependencies — no `slowapi` or Redis install needed
- ~50 lines of self-contained code, trivially auditable
- Transparent to the endpoint handler: middleware applies before the route is reached
- Returns proper 429 with `Retry-After` header, so well-behaved clients can back off
- Correct for single-process deployments (dev, Streamlit Cloud, Render free tier)

**Negative:**
- **Per-worker counters** — if scaled to multiple `uvicorn` workers, each process has its own window. A client could double the effective limit by spraying requests across workers. Acceptable at portfolio scale; switch to Redis-backed `slowapi` if multi-worker becomes necessary.
- **In-memory reset on restart** — the counter is not persisted; a server restart resets every client to zero.
- **IP-based only** — no concept of authenticated users yet (no auth system exists). Clients behind a shared NAT will share a rate limit.

**Neutral:**
- Default limit: 2 requests per 60 seconds per IP, configurable at middleware registration
- Only tracks `POST /api/analyze`; `GET /api/health` is unrestricted
