# AGENTS.md

## Setup & commands

```bash
uv venv && uv pip install -e ".[dev]"                 # install deps
.venv/bin/python -m bill_advisor.extraction <pdf>     # extract → JSON
.venv/bin/python -m bill_advisor.audit <pdf>          # extract + audit
.venv/bin/streamlit run app.py                        # UI (dev)
.venv/bin/uvicorn api.main:app --reload --port 8000   # FastAPI
ruff check .                                          # lint

# Docker (prod-like local test)
docker build -t bill-advisor .
docker run -p 80:8501 -p 8001:8001 \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  -e ESIOS_TOKEN=your-token \
  -v ~/bill-advisor-logs:/app/logs \
  bill-advisor

# Deploy (push to main auto-deploys, or manual from Actions tab)
```

## Architecture

- **schemas.py** — Pydantic domain model. 11 models (root Factura + 10 sub-models), single source of truth.
- **extraction.py** — Claude Opus 4.7 via `tool_use` forced (NOT `messages.parse` — schema too complex for grammar compiler). System prompt + tool schema are prompt-cached (`cache_control: ephemeral`). ~90% cost reduction on repeat calls.
- **audit.py** — Pure logic (no LLM). 10 deterministic checks. Each is a `_check_*` function returning `list[Finding]`. Sorted critical → warning → info. The PVPC comparison check (`_check_pvpc_comparison`) is the only one that makes HTTP calls.
- **comparator.py** — PVPC tariff comparison engine. Compares a libre fija bill against PVPC for the same period. Only `comparator.py` + `pvpc_client.py` know about ESIOS.
- **pvpc_client.py** — ESIOS indicator #1001 fetcher. Returns hourly PVPC 2.0TD prices in €/kWh.
- **logger.py** — stdlib logging with stdout (Docker logs) + file handler (`/app/logs/bill-advisor.log`).
- **metrics.py** — Prometheus counters + histogram with embedded HTTP server on port 8001. Tracks sessions, extractions, errors, PVPC results, chat activity, extraction duration.
- **api/main.py** — FastAPI with `GET /api/health`, `POST /api/analyze`. CORS for localhost:3000.
- **api/rate_limiter.py** — In-memory sliding-window rate limiter: 2 req/min per IP on POST `/api/analyze`.
- **app.py** — Streamlit UI. Caches PDF extraction per session (`@st.cache_data`). Includes a RAG chat ("Pregunta sobre tu factura") backed by corpus docs in `bill_advisor/rag/corpus/`.
- **bill_advisor/rag/query.py** — Claude Sonnet 4 Q&A function. Loads all `.md` corpus docs at import; accepts question + Factura JSON, returns plain-Spanish answer. System prompt is prompt-cached.

## Domain model quirks (critical for extraction quality)

- PVPC vs Libre: In PVPC, `Energia.importe_energia_*` = only peajes (~15-20% of real cost). The rest lives in `CostesPVPC`. In libre, `importe_energia_*` = total cost and `costes_pvpc` = null.
- Distribuidora ≠ comercializadora. Don't infer one from the other.
- Only 5 CORs can sell PVPC: Curenergía (Iberdrola), Energía XXI (Endesa), Comercializadora Regulada (Naturgy), Régsiti (Repsol), Baser (EDP).
- The system prompt (extraction.py:20-164) is ~3000 tokens of Spanish electricity domain rules. Edit it to fix extraction failures, not the schema.

## Environment

| Variable | Required | Source |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | `.env` (gitignored) or GitHub secret |
| `ESIOS_TOKEN` | Yes (for PVPC comparator) | `.env` (gitignored) or GitHub secret |

- **Local dev:** `load_dotenv()` at module level in `app.py` and `api/main.py`. In `extraction.py` only inside the `if __name__ == "__main__"` CLI guard.
- **Production (Lightsail):** Keys passed via `-e` flags from GitHub Actions secrets — never written to disk.

## Testing

No tests exist yet. Design supports testing:
- `extract_factura()` accepts optional `client: anthropic.Anthropic | None` for DI
- `audit.py` is pure logic — easiest targets for first tests
- `pvpc_client.fetch_pvpc_prices()` accepts optional `esios_token` for DI
- `comparator.compare_with_pvpc()` is pure logic (no IO)
- Fixture JSONs in `tests/fixtures/` (gitignored, only `.gitkeep` tracked)

## Linting

Ruff, line-length 100, target py310. Rules: E, F, I, UP, B, SIM. No mypy, no CI.

## Package layout

Flat — `bill_advisor/` and `api/` at repo root, both built as wheel packages by hatchling.

## PVPC Comparator

- Only triggers for `modalidad != "PVPC"` bills
- Fetches hourly PVPC 2.0TD prices (ESIOS indicator #1001, Península) for the billing period
- Distributes the factura's kWh uniformly across hours in each period (punta/llano/valle)
- Recomputes energy cost at PVPC rates; keeps potencia and tax rates from the original bill
- Reports **both directions**: PVPC cheaper → finding with `ahorro_estimado_eur_mes`; PVPC more expensive → info finding explaining the volatility hedge
- The savings estimate carries a disclaimer: uniform distribution, not real hourly data
- If ESIOS is down, the check silently returns `[]` — pipeline never breaks
