# Bill Advisor

AI-powered analysis of Spanish residential electricity bills (facturas eléctricas). Upload a factura PDF, get a structured breakdown of every charge, audit findings on anomalies, and savings opportunities — all in plain Spanish.

**Status:** Phase 1 MVP. Extracts, audits, and compares against the PVPC regulated tariff. Datadis hourly integration is Phase 2.

## What it does

1. **Extracts** every line of a Spanish electricity bill into a typed schema using Claude vision — handles all major comercializadoras (Iberdrola, Endesa, Naturgy, Octopus, Repsol, COR/PVPC, etc.) without per-layout parsers.
2. **Audits** the extracted data against a set of deterministic rules — math integrity, IVA validity, contador rental, PVPC component allocation, otros_servicios cancellation candidates, autoconsumo opportunities, and PVPC tariff comparison.
3. **Surfaces** findings ranked by severity (critical / warning / info) with quantified annual savings where applicable.

PVPC tariff comparison is built in (see "PVPC Comparator" in [`AGENTS.md`](AGENTS.md)). Hourly-consumption analysis remains Phase 2 — see [Next Steps](docs/next-steps.md).

## Quick start

Requires Python ≥ 3.10, `uv`, and an [Anthropic API key](https://console.anthropic.com/). For PVPC tariff comparison you also need an [ESIOS token](https://api.esios.ree.es/).

```bash
git clone <repo>
cd bill-advisor
uv venv
uv pip install -e .

# Create .env with API keys (unquoted values for Docker compat)
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env
echo "ESIOS_TOKEN=your-esios-token" >> .env

# CLI extraction
.venv/bin/python -m bill_advisor.extraction path/to/factura.pdf

# CLI extraction + audit
.venv/bin/python -m bill_advisor.audit path/to/factura.pdf

# Streamlit UI (debug / quick demos)
.venv/bin/streamlit run app.py

# FastAPI server (production UI backend — consumed by the Next.js frontend)
.venv/bin/uvicorn api.main:app --reload --port 8000

# Docker (production)
docker build -t bill-advisor .
docker run -p 8501:8501 --env-file .env -v ~/bill-advisor-logs:/app/logs bill-advisor
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
│   or API)    │      │   tool use)          │      └──────┬───────┘
└──────────────┘      └──────────────────────┘             │
                                                             │
                                                             ▼
                                                     ┌───────────────┐
                                                     │  audit.py     │
                                                     │  (10 checks)  │
                                                     │               │
                                                     │  ┌──────────┐ │
                                                     │  │ PVPC     │─│──▶ pvpc_client.py
                                                     │  │ compare  │ │       │ ESIOS
                                                     │  └──────────┘ │       ▼
                                                     └───────┬───────┘  ┌──────────────┐
                                                             │          │ comparator   │
                                                             ▼          │ .py (recalc) │
                                                     ┌──────────────┐   └──────┬───────┘
                                                     │  Findings    │◀─────────┘
                                                     │  (sorted by  │
                                                     │   severity)  │
                                                     └──────┬───────┘
                                                             │
                                        ┌────────────────────┼────────────────────┐
                                        │                    │                    │
                                        ▼                    ▼                    ▼
                                  ┌──────────┐       ┌───────────┐       ┌──────────────┐
                                  │  app.py  │       │ api/main  │       │  rag/query.py│
                                  │ Streamlit│       │  FastAPI  │       │  (corpus     │
                                  │  UI +    │       │ + rate_   │       │   Q&A chat)  │
                                  │  chat    │       │ limiter   │       │              │
                                  └──────────┘       └───────────┘       └──────────────┘
                                  │                    │
                                  └────────────────────┘
                                              │
                                              ▼
                                      ┌──────────────┐
                                      │  logger.py   │
                                      │  stdout +    │
                                      │  /app/logs/  │
                                      └──────────────┘
```

**Modules:**

| Module | Responsibility |
|---|---|
| `bill_advisor/schemas.py` | Pydantic models for `Factura`. Single source of truth with 11 models. |
| `bill_advisor/extraction.py` | Claude API call: PDF → tool-use forcing the `record_factura_extraida` schema. System prompt + tool schema prompt-cached (~90% cost saving on repeats). |
| `bill_advisor/audit.py` | 10 deterministic anomaly checks against a validated `Factura`. No LLM. The PVPC comparison check (`_check_pvpc_comparison`) internally delegates to `comparator.py`. |
| `bill_advisor/comparator.py` | PVPC tariff recompute engine: distributes kWh uniformly across hours per period, recomputes cost at hourly PVPC rates, returns `ComparisonResult`. |
| `bill_advisor/pvpc_client.py` | ESIOS API client — fetches indicator #1001 (PVPC 2.0TD Península hourly prices). Returns `dict[date, dict[int, float]]` in €/kWh. |
| `bill_advisor/logger.py` | Module-level logger with two handlers: stdout (Docker logs) + file (`/app/logs/bill-advisor.log`). Messages prefixed `[Bill Advisor]`. |
| `bill_advisor/rag/query.py` | Claude Sonnet 4 Q&A backed by 7 corpus `.md` files in `rag/corpus/`. Accepts `messages` list for conversation memory. Prompt-cached system prompt. |
| `api/main.py` | FastAPI server with `GET /api/health` and `POST /api/analyze`. CORS for localhost:3000. Wraps extraction + audit. |
| `api/rate_limiter.py` | In-memory sliding-window rate limiter: 10 req/min per IP on POST `/api/analyze`. Returns 429 with `Retry-After`. |
| `app.py` | Streamlit UI. Single-page: upload → extraction → audit → findings + RAG chat. Conversation stored in session state (not backend). |

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
- [ADR-0013](docs/adr/0013-rate-limiting-strategy.md) — In-memory rate limiting (2 req/min per IP)
- [ADR-0014](docs/adr/0014-structured-logging.md) — Structured logging with stdlib `logging`

## What's next

See [`docs/next-steps.md`](docs/next-steps.md). Headline items:

## Disclaimers

- Outputs are **educativos**, never financial or regulatory advice.
- "Ahorro estimado €X/año" figures are based on the single bill extracted and assume similar consumption patterns going forward — they're estimates, not guarantees.
- Always verify extracted values against the original factura. The extractor's `notas_extraccion` flags anything that needed inference or human review.

## License

MIT.
