# ADR-0015: Prometheus metrics for usage monitoring

**Status:** Accepted
**Date:** 2026-06-15

## Context

The application lacked a way to monitor usage at a glance. The only insight into activity was SSHing into Lightsail and running `docker logs | grep`. No extraction counts, error rates, PVPC comparison stats, or session tracking existed — making it impossible to tell if the tool was being used, breaking, or delivering value.

Two prior approaches were considered but never implemented:
1. **Plausible / simple analytics** — good for page views, but can't track API-level events (PVPC hits, extraction duration, errors).
2. **Docker log greps via cron** — free and simple, but requires SSH access and provides no historical trends.

## Decision

Use the `prometheus_client` Python library with an embedded HTTP server on port 8001 (`bill_advisor/metrics.py`).

### Metrics tracked

| Metric | Type | Labels | Purpose |
|---|---|---|---|
| `bill_sessions_total` | Counter | none | Unique browser sessions (via `st.session_state` guard) |
| `bill_extractions_total` | Counter | none | Successful PDF extractions |
| `bill_extraction_errors_total` | Counter | none | Failed extractions (API errors, schema validation) |
| `bill_pvpc_savings_found_total` | Counter | none | PVPC was cheaper than current tariff |
| `bill_pvpc_more_expensive_total` | Counter | none | Current tariff was cheaper than PVPC |
| `bill_chat_questions_total` | Counter | none | RAG questions asked via chat |
| `bill_extraction_duration_seconds` | Histogram | none | Wall time of extraction + audit pipeline (buckets: 5–120s) |

### Architecture

- Metrics defined in `bill_advisor/metrics.py` as module-level globals.
- `prometheus_client.start_http_server(8001)` fires at import time — before Streamlit's main loop — so the metrics endpoint is available immediately on container boot.
- Module-level counters avoid Streamlit's script re-execution issue (counters would register twice if defined inside `app.py`).
- Alloy agent on the Lightsail host scrapes `localhost:8001` and pushes to Grafana Cloud.

## Consequences

**Positive:**
- Standard Prometheus text format — industry standard, trivially scraped by any observer.
- Zero new system dependencies — pure Python, no system packages needed.
- Grafana Cloud free tier (10k series, 3 dashboards) is more than sufficient for ~7 metrics.
- Alloy agent handles transport: scrape → remote write. No config changes to the container.
- The embedded HTTP server is invisible to the Streamlit UI — port 8001 is separate from 8501.

**Negative:**
- Exposes an HTTP port (8001) that serves data. The metrics contain no PII (no IPs, user IDs, or CUPS), but a determined attacker could infer activity patterns. Acceptable for a portfolio app.
- Port 8001 must be explicitly mapped via `-p 8001:8001` in the Docker run command — easy to forget.
- No authentication on the metrics endpoint. Again, no PII, no write access — acceptable.

**Neutral:**
- Alloy config is ~15 lines of HCL. Must be configured once per Lightsail instance.
- Metric names use `snake_case` with `_total` suffix (Prometheus convention for counters). The `_total` suffix is automatically appended by `prometheus_client` — Grafana queries use `bill_sessions_total` even though the code says `bill_sessions`.
