# Bill Advisor

AI-powered analysis of Spanish residential electricity bills (facturas eléctricas). Upload a factura PDF, get a structured breakdown of every charge, audit findings on anomalies, and savings opportunities — all in plain Spanish.

**Status:** Phase 1 MVP. Extracts, audits, and compares against the PVPC regulated tariff. Datadis hourly integration is Phase 2.

## What it does

1. **Extracts** every line of a Spanish electricity bill into a typed schema using Claude vision — handles all major comercializadoras (Iberdrola, Endesa, Naturgy, Octopus, Repsol, COR/PVPC, etc.) without per-layout parsers.
2. **Audits** the extracted data against a set of deterministic rules — math integrity, IVA validity, contador rental, PVPC component allocation, otros_servicios cancellation candidates, autoconsumo opportunities, and PVPC tariff comparison.
3. **Surfaces** findings ranked by severity (critical / warning / info) with quantified annual savings where applicable.

PVPC tariff comparison is built in (see "PVPC Comparator" in [`AGENTS.md`](AGENTS.md)). Hourly-consumption analysis remains Phase 2 — see [Next Steps](docs/next-steps.md).

## Quick start

Requires Python ≥ 3.10 and `uv`. Anthropic API key needed.

```bash
git clone <repo>
cd bill-advisor
uv venv
uv pip install -e .

# Create .env with your API key
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env

# CLI extraction
.venv/bin/python -m bill_advisor.extraction path/to/factura.pdf

# CLI extraction + audit
.venv/bin/python -m bill_advisor.audit path/to/factura.pdf

# Streamlit UI (debug / quick demos)
.venv/bin/streamlit run app.py

# FastAPI server (production UI backend — consumed by the Next.js frontend)
.venv/bin/uvicorn api.main:app --reload --port 8000
```

### API endpoints

Once the FastAPI server is running on `http://localhost:8000`:

| Method | Path            | Body                  | Returns                                      |
|--------|-----------------|-----------------------|----------------------------------------------|
| GET    | `/api/health`   | —                     | `{"status": "ok"}`                           |
| POST   | `/api/analyze`  | `multipart/form-data` with `pdf` field | `{"factura": {...}, "findings": [...]}` |

Auto-generated docs (Swagger UI) live at `http://localhost:8000/docs`.

## Architecture

```
┌──────────────┐      ┌──────────────────────┐      ┌──────────────┐
│  PDF bytes   │ ───▶ │  extraction.py       │ ───▶ │  Factura     │
│  (Streamlit  │      │  (Claude vision +    │      │  (Pydantic)  │
│   or CLI)    │      │   tool use)          │      └──────┬───────┘
└──────────────┘      └──────────────────────┘             │
                                                            ▼
                                                    ┌──────────────┐
                                                    │  audit.py    │
                                                    │  (9 rule     │
                                                    │   checks)    │
                                                    └──────┬───────┘
                                                            │
                                                            ▼
                                                    ┌──────────────┐
                                                    │  Findings    │
                                                    │  (sorted by  │
                                                    │   severity)  │
                                                    └──────────────┘
```

**Modules:**
- `bill_advisor/schemas.py` — Pydantic models for the extracted `Factura`. Includes a PVPC-specific `CostesPVPC` sub-block.
- `bill_advisor/extraction.py` — Claude API call: PDF as `document` block + tool use forcing the `record_factura_extraida` schema. System prompt + tool schema are prompt-cached.
- `bill_advisor/audit.py` — Pure-logic anomaly checks against a validated `Factura`. No LLM.
- `api/main.py` — FastAPI HTTP layer wrapping extraction + audit. Designed to be consumed by the Next.js frontend (`web/`, scaffolded next).
- `app.py` — Streamlit UI (kept for quick local testing / debugging).

## Design decisions

Key decisions are documented as ADRs in [`docs/adr/`](docs/adr/). Highlights:

- [ADR-0001](docs/adr/0001-vision-llm-for-pdf-extraction.md) — Vision LLM (not OCR + regex per-layout)
- [ADR-0002](docs/adr/0002-tool-use-not-messages-parse.md) — Tool-use API path, not `messages.parse` (schema complexity blew the grammar compiler)
- [ADR-0004](docs/adr/0004-pvpc-sub-block-schema.md) — PVPC sub-block in the schema (the first extraction missed mercado mayorista entirely)
- [ADR-0005](docs/adr/0005-pdf-first-datadis-later.md) — PDF-first input strategy
- [ADR-0008](docs/adr/0008-prompt-caching.md) — Caching strategy (~90% input-cost saving on repeated extractions)
- [ADR-0009](docs/adr/0009-direct-esios-over-mcp.md) — Direct ESIOS call (not MCP) for PVPC prices
- [ADR-0010](docs/adr/0010-uniform-kwh-distribution.md) — Uniform kWh distribution in PVPC comparison
- [ADR-0011](docs/adr/0011-deterministic-audit.md) — Deterministic audit (zero LLM)
- [ADR-0012](docs/adr/0012-defer-tests-and-ci.md) — Defer tests and CI to post-MVP

## What's next

See [`docs/next-steps.md`](docs/next-steps.md) for the prioritized roadmap. Headline items:
1. Test extraction + PVPC comparator against real bills from multiple comercializadoras
2. Polish deferred items (prompt rule 10, annual savings framing, schema naming)
3. Write unit tests for `audit.py` and `comparator.py`
4. RAG explainer corpus (plain-Spanish line-by-line explanations)
5. Deploy to Streamlit Cloud with demo mode
6. Phase 2 — Datadis integration for hourly consumption

## Disclaimers

- Outputs are **educativos**, never financial or regulatory advice.
- "Ahorro estimado €X/año" figures are based on the single bill extracted and assume similar consumption patterns going forward — they're estimates, not guarantees.
- Always verify extracted values against the original factura. The extractor's `notas_extraccion` flags anything that needed inference or human review.

## License

MIT.
