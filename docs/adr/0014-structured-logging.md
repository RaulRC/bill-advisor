# ADR-0014: Structured logging with stdlib logging

**Status:** Accepted
**Date:** 2026-06-05

## Context

The application originally used `print()` statements scattered across three entry points:

- `app.py` — Streamlit UI (7 call sites)
- `api/main.py` — FastAPI server (11 call sites)
- `api/rate_limiter.py` — Rate limit middleware (1 call site)

Each `print()` formatted its own message prefix manually (`[Bill Advisor]` vs `[Bill Advisor API]`), making the format inconsistent. All output went exclusively to stdout:

- **Pro:** `docker logs` worked out of the box.
- **Con:** No persistent log file survives a container restart. If the container crashes or is rebuilt, all prior logs are lost.
- **Con:** No log levels — `print()` treated errors, warnings, and informational messages identically, so commands like `docker logs | grep -i error` were useless.
- **Con:** Adding structured context (timestamps, module name) required editing every call site.

## Alternatives considered

1. **Status quo (`print()` everywhere)** — simplest, but no persistence, no levels, no grepability. Rejected.

2. **stdlib `logging`** — built-in, zero dependencies, supports multiple handlers (stdout + file), log levels, configurable format. The team is familiar with it.

3. **`loguru`** — nicer API (`logger.info("got {} items", n)`), auto-rotation, serialization. Requires an extra dependency and adds a learning curve for future contributors.

4. **`structlog`** — structured JSON logs ideal for log aggregation (ELK, Datadog). Over-engineered at current scale (single container, no log pipeline).

5. **JSON logging via stdlib** — future possibility: add a `JsonFormatter` to the file handler without changing any call sites. Not needed today.

## Decision

Use stdlib `logging` with a module-level singleton in `bill_advisor/logger.py`:

- **Two handlers:**
  - `logging.StreamHandler(sys.stdout)` — for `docker logs` (same as `print()`)
  - `logging.FileHandler("/app/logs/bill-advisor.log")` — persists across restarts via Docker volume mount (`-v ~/bill-advisor-logs:/app/logs`)
- **Format:** `[Bill Advisor] %(message)s` — matches the previous `[Bill Advisor]` prefix convention
- **Levels used:** `info()` for normal operations, `warning()` for rate limits, `error()` for exceptions
- **Distinguishing sources:** API module prepends `[API]` to its messages inline (e.g. `[Bill Advisor] [API] POST /api/analyze — ...`). Streamlit emits bare messages.
- **No per-module loggers** — one logger for the entire app keeps things simple at current scale.

## Consequences

**Positive:**
- Logs survive container restarts via the persistent volume mount.
- `docker logs` continues to work as before (stdout handler).
- Log levels allow filtering: `docker logs bill-advisor 2>&1 | grep -i error` now works.
- Adding structured context (timestamps, module names, request IDs) later requires only editing the formatter — no call-site changes.
- The `logger` import is a drop-in replacement for `print()`: same number of characters, same call pattern.

**Negative:**
- Hardcoded `/app/logs/` path couples the logger to the Docker deployment. On bare-metal or Streamlit Cloud, the `FileHandler` will still create the directory and log file, but the path won't be meaningful — acceptable for a Docker-first project.
- Single logger means all modules share the same log level. If we need fine-grained per-module control later, we switch to `logging.getLogger(__name__)` per module (no structural change required).
- No log rotation — a high-traffic deployment could fill the volume over time. Mitigation: at portfolio scale (a few requests/day), this is a non-issue. Add a `RotatingFileHandler` or `TimedRotatingFileHandler` if needed.

**Neutral:**
- Using `logging.FileHandler` (not `RotatingFileHandler`) keeps the implementation simple. Rotation can be added later without changing call sites.
- Third-party log libraries (`loguru`, `structlog`) remain an option for Phase 2 if log aggregation is introduced.
