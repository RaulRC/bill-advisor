# ADR-0010: Uniform kWh distribution for PVPC comparison

**Status:** Accepted
**Date:** 2026-06-03

## Context

The PVPC comparator (`comparator.py`) needs to estimate what a consumer *would have paid* under the PVPC tariff given their actual consumption. The factura only provides total kWh per time period (punta/llano/valle) — not hourly consumption.

Two approaches:
1. **Uniform distribution** — divide each period's kWh evenly across all hours in that period
2. **Real hourly profiles** — use Datadis API to fetch actual hourly consumption data

## Decision

Use uniform distribution within each period.

## Consequences

**Positive:**
- Zero additional API calls or credentials (Datadis requires the consumer's CUPS authorization)
- Works for any factura without the consumer needing to opt into data sharing
- Simple, explainable computation

**Negative:**
- Accuracy varies: if the consumer concentrates usage in expensive PVPC hours (e.g., 20-22h), the uniform model *underestimates* actual PVPC cost; if they use cheap hours (sunny 14-16h), it *overestimates*
- Results carry a disclaimer visible in the UI and API response

**Mitigation:**
- The finding text explicitly states: *assuming uniform distribution, not your real hourly consumption*
- Phase 2 can add Datadis integration for consumers who authorize it, producing a more accurate estimate
