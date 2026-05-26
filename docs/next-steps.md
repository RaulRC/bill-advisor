# Next Steps

Phase 1 (PDF extraction + audit + Streamlit UI) is functionally complete. This document captures what's deliberately deferred, in roughly the order I'd tackle it next.

## 1. Real-world test set (highest signal-to-noise)

The system has only been validated against one factura (PVPC, Naturgy COR group, Toledo, autoconsumo). One bill is not enough to know where the schema or prompt break.

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

This generates the data that shapes everything else below.

## 2. Polish items deferred from Phase 1

Known issues to fix once we have real signal from #1:

- **Prompt rule 10 noise.** The model uses `notas_extraccion` for both genuine "needs human review" notes AND self-documentation ("I applied the PVPC mapping rule correctly"). Tighten the rule to explicitly forbid the latter category.
- **`subtotal_sin_impuestos_eur` semantic ambiguity.** Different bills use different conventions for what "subtotal" means (strict pre-tax vs base imponible IVA). Split into `subtotal_pre_impuestos_eur` and `base_imponible_iva_eur`, both checkable.
- **Savings figures framing.** `ahorro_estimado_eur_mes` confuses next to the bill's actual monthly cost. Switch UI to annual ("~€10/año") for clearer call-to-action.
- **Alquiler contador finding dedup.** Currently shows up twice (as a warning + as a nota_extractor). Once rule 10 is tightened, the duplicate nota should disappear; verify.

## 3. RAG explainer

The auditor answers "what's anomalous?". The original plan had a second AI flow answering "what is this charge, in normal Spanish?" — for users who don't know what "peajes T+D" or "margen comercialización" means.

**Scope:** ~15 markdown documents in `bill_advisor/rag/corpus/` covering:
- CNMC's tariff terminology
- OCU / Facua glossaries
- BOE definitions of cargos y peajes
- Bono social mechanics
- Autoconsumo modalities (1-5 vs 21-22)

**Flow:** when user clicks a finding or a bill line, Claude looks up relevant corpus docs and explains the concept in plain Spanish, cited.

**Effort:** ~1 weekend including corpus curation.

## 4. Deploy to Streamlit Cloud

Phase 1 portfolio target. Free tier, GitHub-backed, configure `ANTHROPIC_API_KEY` as a secret.

**Prerequisites before deploying:**
- Push repo to GitHub (private or public)
- Add Streamlit Cloud's IP to API key allowlist (if using one)
- Add a usage cap or rate limiter — public demos get scraped
- Add a "demo mode" with a pre-loaded anonymized factura so visitors see something without uploading

## 5. Phase 2 — Datadis integration

The real differentiator. Datadis exposes hourly consumption (CCH) once the user authorizes via NIF + CUPS.

**Phase 2 unlocks:**
- True tariff simulation (run user's actual consumption against alternative tariffs)
- Time-shifting recommendations ("shift dishwasher to 03:00") backed by hourly data and your existing day-ahead price forecast
- Quantified autoconsumo opportunity (how much solar gets vertido vs autoconsumido instantáneamente)
- Optimal potencia contratada recommendation (P95 of actual peak)

**Annoying part:** Datadis auth requires a registered "empresa" or that you operate as the user. Friction will need design work.

**Reuse opportunity:** this plugs directly into the existing Spanish electricity forecast project — the price forecast feeds the time-shifting advisor.

## 6. Cross-comercializadora tariff comparator

Documented in [ADR-0006](adr/0006-same-comercializadora-only.md). Deferred from Phase 1.

**Approach (option b from the ADR):** curate 6-8 reference tariffs as YAML in `bill_advisor/tariffs/` (cheapest PVPC reference, cheapest indexed, cheapest fixed for low/medium/high consumption, a self-consumption-friendly one, an EV-friendly one). Maintain quarterly. Simulate user's bill on each. Report range, not single winner.

**Honest framing:** "comparado con N tarifas de referencia, con tu mismo consumo facturarías €X (rango €X-€Y)" — never "switch to Y, save €Z."

## 7. Multi-bill history

If a user uploads multiple bills over time, surface trends — consumption growth, price drift, seasonality. Lower-priority than the above; mostly portfolio polish.
