# Next Steps

Phase 1 (PDF extraction + audit + PVPC comparator + Streamlit UI) is functionally complete. This document captures what's deliberately deferred, in roughly the order I'd tackle it next.

## 1. Real-world test set (highest signal-to-noise)

The system has only been validated against one factura (PVPC, Naturgy COR group, Toledo, autoconsumo). One bill is not enough to know where the schema, prompt, or comparator break.

**Action:** collect 4-5 anonymized facturas from different comercializadoras and modalidades:
- Iberdrola libre fija
- Endesa libre indexada
- Octopus Energy / Holaluz indexada
- Repsol / TotalEnergies libre fija
- Another PVPC bill (different distribuidora — e-distribución, i-DE)

Run each through `python -m bill_advisor.audit <pdf>` and note:
- Which fields the extractor missed or got wrong
- Which audit findings were spurious
- Which schema gaps showed up
- Whether the PVPC comparator's savings estimate seems reasonable (spot-check a few hours manually against the ESIOS API)

This generates the data that shapes everything else below.

## 2. Polish items deferred from Phase 1

Known issues to fix once we have real signal from #1:

- **Prompt rule 10 noise.** The model uses `notas_extraccion` for both genuine "needs human review" notes AND self-documentation ("I applied the PVPC mapping rule correctly"). Tighten the rule to explicitly forbid the latter category.
- **`subtotal_sin_impuestos_eur` semantic ambiguity.** Different bills use different conventions for what "subtotal" means (strict pre-tax vs base imponible IVA). Split into `subtotal_pre_impuestos_eur` and `base_imponible_iva_eur`, both checkable.
- **Savings figures framing.** `ahorro_estimado_eur_mes` confuses next to the bill's actual monthly cost. Switch UI to annual ("~€10/año") for clearer call-to-action.
- **Alquiler contador finding dedup.** Currently shows up twice (as a warning + as a nota_extractor). Once rule 10 is tightened, the duplicate nota should disappear; verify.

## 3. Unit tests

The codebase was designed for testability from day one. Write tests starting with the highest-signal targets:

- **`audit.py`** — pure logic (except `_check_pvpc_comparison`). Pass a `Factura` fixture, assert on returned findings. No mocking needed for 9 of 10 checks.
- **`comparator.py`** — pure logic. Pass a `Factura` + prices dict, assert on `ComparisonResult`.
- **`pvpc_client.py`** — requires an `esios_token` for integration tests; defer or mock `httpx`.

Fixture JSONs live in `tests/fixtures/` (gitignored, only `.gitkeep` tracked).

## 4. GitHub Actions CI

Once tests exist, add:
- `ruff check .` on every push
- `pytest` on every push
- Optional: mark PVPC client tests as integration (skip unless `ESIOS_TOKEN` is set)

Dockerfile / Streamlit Cloud deploy config can be added alongside.

## 5. RAG explainer

The auditor answers "what's anomalous?". A separate AI flow would answer "what is this charge, in normal Spanish?" — for users who don't know what "peajes T+D" or "margen comercialización" means.

**What's done:** first corpus document committed — `bill_advisor/rag/corpus/pvpc-vs-libre-fija.md`.

**Remaining:** ~15 markdown documents in `bill_advisor/rag/corpus/` covering:
- CNMC's tariff terminology
- OCU / Facua glossaries
- BOE definitions of cargos y peajes
- Bono social mechanics
- Autoconsumo modalities (1-5 vs 21-22)

**Flow:** when user clicks a finding or a bill line, Claude looks up relevant corpus docs and explains in plain Spanish, cited.

**Effort:** ~1 weekend including corpus curation.


## 8. Phase 2 — Datadis integration

The real differentiator. Datadis exposes hourly consumption (CCH) once the user authorizes via NIF + CUPS.

**Phase 2 unlocks (still pending):**
- Replace uniform kWh distribution with real hourly data for PVPC comparison
- Time-shifting recommendations ("shift dishwasher to 03:00") backed by hourly data and day-ahead price forecast
- Quantified autoconsumo opportunity (solar vertido vs autoconsumido)
- Optimal potencia contratada recommendation (P95 of actual peak)

**Reuse opportunity:** this plugs into the existing Spanish electricity forecast project — the price forecast feeds the time-shifting advisor.

## 9. Cross-comercializadora tariff comparator

Documented in [ADR-0006](adr/0006-same-comercializadora-only.md). Deferred from Phase 1.

**Approach (option b from the ADR):** curate 6-8 reference tariffs as YAML in `bill_advisor/tariffs/` (cheapest PVPC reference, cheapest indexed, cheapest fixed for low/medium/high consumption, a self-consumption-friendly one, an EV-friendly one). Maintain quarterly. Simulate user's bill on each. Report range, not single winner.

**Now closer:** the PVPC comparison engine and comparator infrastructure are ready; adding more reference tariffs is mostly data entry.

**Honest framing:** "comparado con N tarifas de referencia, con tu mismo consumo facturarías €X (rango €X-€Y)" — never "switch to Y, save €Z."

## 10. Multi-bill history

If a user uploads multiple bills over time, surface trends — consumption growth, price drift, seasonality. Lower-priority than the above; mostly portfolio polish.
