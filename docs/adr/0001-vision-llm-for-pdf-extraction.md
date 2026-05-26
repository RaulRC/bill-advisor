# ADR-0001: Use a vision LLM for PDF extraction

**Status:** Accepted

## Context

Spanish electricity bills vary wildly by comercializadora — Iberdrola, Endesa, Naturgy, Octopus, Repsol, COR (PVPC), and dozens of smaller players each ship their own PDF layout. Field positions, terminology, even the placement of CUPS and distribuidora differ from one company to another. The bills are also visually complex: tables, fine print, footnotes, embedded images.

A traditional OCR + regex extraction pipeline would require building and maintaining a parser per comercializadora layout (15+ in active use), with edge cases for legacy templates, holiday-period bills, autoconsumo formats, etc. This is expensive to build and brittle when comercializadoras redesign their bills (which happens once or twice a year).

## Decision

Pass the PDF bytes directly to Claude (Opus 4.7) as a `document` content block and use tool use with a Pydantic schema to extract structured data. No OCR step, no per-layout code.

## Alternatives considered

- **OCR (Tesseract / AWS Textract) + regex per layout.** High build and maintenance cost. Every Iberdrola redesign breaks the parser. Rejected.
- **Vision LLM with fine-tuning.** Cheaper per inference but expensive to set up and not worth it for a portfolio-scale project. Rejected.
- **Datadis API only (skip PDF entirely).** Datadis requires user OAuth via NIF + CUPS authorization — high onboarding friction. Also missing tariff details that only the PDF contains (comercializadora's commercial plan name, exact descuentos, etc.). Deferred to Phase 2 (see [ADR-0005](0005-pdf-first-datadis-later.md)).

## Consequences

**Positive:**
- Layout-agnostic — same code path handles every Spanish comercializadora.
- Iteration speed — schema changes are prompt edits, not parser rewrites.
- Self-correcting via `notas_extraccion` — the model flags ambiguities for human review instead of failing silently.

**Negative:**
- Cost: ~€0.04 per extraction at current Opus 4.7 pricing (mitigated by prompt caching — see [ADR-0008](0008-prompt-caching.md)).
- Latency: 10-20 seconds per call. Unacceptable for high-volume, fine for one-bill-at-a-time use.
- Possible hallucination on edge cases (low-quality scans, unusual layouts). Mitigated by always surfacing extracted values for user confirmation and using `notas_extraccion` as a hallucination guardrail.
- Hard dependency on Anthropic API — if Anthropic is down, the product is down. Acceptable for Phase 1.
