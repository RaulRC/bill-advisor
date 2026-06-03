# ADR-0012: Defer tests and CI to post-MVP

**Status:** Accepted
**Date:** 2026-06-03

## Context

The project is in early development with a single developer. Writing tests and setting up CI pipelines has an upfront cost.

## Decision

Ship the MVP without automated tests or CI. The repository does not include a `tests/` directory (only `.gitkeep`) or GitHub Actions config.

## Consequences

**Positive:**
- Faster iteration velocity during the initial feature-building phase
- No CI debugging overhead (misconfigured runners, flaky tests, cache misses)
- Lower cognitive load for a single developer

**Negative:**
- **Regression risk** — no safety net when refactoring `audit.py` or `extraction.py`
- **No quality signal** — cannot automatically verify that a PR doesn't break existing functionality
- **Accruing technical debt** — the longer tests are deferred, the harder they are to write (code becomes more coupled, test patterns diverge)

**When to revisit:**
- Add `pytest` + GitHub Actions when a second contributor joins the project
- Before any production deployment
- Earlier if a regression is caught in production

**The codebase is designed to support testing from day one:**
- `extract_factura()` accepts optional `client: anthropic.Anthropic | None` (DI for mocking)
- `audit.py` checks are pure functions (no mocking needed except `_check_pvpc_comparison`)
- `pvpc_client.fetch_pvpc_prices()` accepts optional `esios_token`
- `comparator.compare_with_pvpc()` is pure logic
