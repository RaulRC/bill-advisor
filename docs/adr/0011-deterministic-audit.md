# ADR-0011: Audit is pure logic (zero LLM)

**Status:** Accepted
**Date:** 2026-06-03

## Context

The project needs to validate extracted factura data for errors, irregularities, and savings opportunities. Two design options:
1. **LLM-powered audit** — feed the extracted data to an LLM and ask it to find issues
2. **Deterministic audit** — hand-written `_check_*` functions for each known pattern

## Decision

Pure deterministic audit (`audit.py`), with each check as a `_check_*` function returning `list[Finding]`.

## Consequences

**Positive:**
- **Testable without mocking** — every check is a pure function (except `_check_pvpc_comparison` which makes one HTTP call). Tests just pass a `Factura` fixture and assert on the returned findings
- **Deterministic** — same input always produces the same output. No hallucination risk
- **Cost-free at inference** — no LLM API calls needed
- **Easy to extend** — add a new `_check_*` function and register it in the `_CHECKS` list

**Negative:**
- Cannot catch novel patterns — only checks written as code are performed
- Upfront engineering cost to encode domain rules that an LLM might know zero-shot (e.g., IVA percentage by year, distributor regions)

**Neutral:**
- Each finding has a stable `code` string (e.g., `iva_calculo_no_cuadra`), enabling UI filtering and API consumers to reference known findings
