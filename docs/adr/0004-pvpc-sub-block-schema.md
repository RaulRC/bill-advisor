# ADR-0004: PVPC sub-block in the schema

**Status:** Accepted

## Context

PVPC (Precio Voluntario para el Pequeño Consumidor) bills decompose the energy cost into four distinct components:

1. **Peajes T+D** (regulated network access fees, per-kWh, per period) — already modeled by `importe_energia_punta/llano/valle_eur`.
2. **Coste de la energía en el mercado mayorista** — pass-through of the hourly OMIE price. Single aggregated number per period.
3. **Margen de comercialización fijo** — regulated retail margin, calculated as `kW × €/kW·año × días/365`. Single aggregated number.
4. **Financiación del bono social** — regulated recargo paid by all consumers. Currently a per-kWh fee, typically billed as a single line.

The initial schema modeled only component 1, treating `Energia.importe_energia_*` as if it represented the *total* energy cost. The first real-bill extraction showed the model correctly identifying components 2-4 but having nowhere to put them, so it stuffed them into `otros_servicios`. This broke downstream calculations: an audit asking "what's the effective €/kWh?" would compute `6.57 / 299 = €0.022/kWh` (absurdly low — only peajes), when the real answer was `40.20 / 299 = €0.134/kWh` (all components).

In mercado libre bills (libre fija or libre indexada), components 2 and 3 are integrated into the `precio €/kWh` and don't appear separately. Component 4 is sometimes broken out, sometimes folded in.

## Decision

Add a `CostesPVPC` Pydantic model with `coste_energia_mercado_mayorista_eur` and `margen_comercializacion_eur`, expose it as an optional `costes_pvpc` field on `Energia`. Populate only when `modalidad == "PVPC"`; null otherwise. Add `coste_financiacion_bono_social_eur` as a top-level field on `OtrosConceptos`, distinct from `descuento_bono_social_eur` (the discount *received* by vulnerable consumers).

## Alternatives considered

- **Flat rename: `importe_energia_*` → `importe_energia_peajes_*`.** Less invasive but forces every downstream calculation to special-case PVPC by looking up extra fields in `otros_servicios`. Rejected as poor ergonomics.
- **Discriminated union: separate `FacturaPVPC`, `FacturaLibreFija`, `FacturaLibreIndexada` classes.** Cleaner long-term but overkill for Phase 1 — most fields are identical across modalidades and copy-paste would breed inconsistency.
- **Generic `components: list[Concepto]` array.** Loses type safety and forces every consumer to filter by string label. Rejected.

## Consequences

**Positive:**
- Audit logic can compute true effective €/kWh under PVPC by summing `importe_energia_* + costes_pvpc.coste_energia_mercado_mayorista_eur + costes_pvpc.margen_comercializacion_eur`.
- Mercado libre extractions are unchanged structurally (just `costes_pvpc = None`).
- Schema preserves the economic meaning of each component: peajes are state-regulated network access; mercado mayorista is pass-through wholesale; margen is what the comercializadora keeps. These behave differently for "where can the customer save?" advice.

**Negative:**
- Schema is larger, contributing to the grammar compilation breakdown that triggered [ADR-0002](0002-tool-use-not-messages-parse.md).
- The bill's visual "Facturación por potencia" line no longer equals `importe_potencia_punta + importe_potencia_valle` — it also includes `costes_pvpc.margen_comercializacion_eur` under PVPC. Downstream audit code must recompose to match the bill's display when verifying line-by-line.
- Doesn't yet cover 3.0TD or 6.1TD tariffs (more periods, different decomposition rules). 2.0TD covers ~99% of residential, acceptable for Phase 1.
