# ADR-0006: Same-comercializadora savings only in Phase 1

**Status:** Accepted

## Context

The most valuable user-facing claim is "switch to comercializadora Y and save €Z per year." That claim requires *tariff data* — not on the user's bill. Three approaches were considered for sourcing it.

The risk is asymmetric: if we tell a user they'll save €200 and they switch and save €50, that's worse than no recommendation. False precision destroys trust faster than honest silence.

## Decision

Phase 1 only attempts **same-comercializadora optimization**: given the user's current comercializadora, Claude looks up the company's current public catalog and proposes a cheaper plan from the same provider, if one exists. No cross-comercializadora comparison. No quantified switching recommendations.

Cross-comercializadora comparison via a curated reference-tariff database is documented and deferred (see [`docs/next-steps.md`](../next-steps.md) §6).

## Alternatives considered

- **Curated reference tariffs (YAML).** Maintain ~6-8 representative tariffs (cheapest PVPC reference, cheapest indexed, cheapest fixed for low/medium/high consumption, a solar-friendly one, an EV-friendly one) in version control. Quarterly review. Simulate user's bill on each. Defensible, but adds maintenance burden before we have a single real user.
- **CNMC comparator integration.** The CNMC operates an official neutral comparator. Best data quality. Legally and technically complex to integrate; defer until there's demand.
- **Defer all savings claims to Phase 2.** Phase 1 becomes a pure auditor / explainer with no recommendation surface. Loses the headline value.

## Consequences

**Positive:**
- No tariff database to maintain. Same-comercializadora lookups happen on demand via the LLM.
- Recommendations are inherently conservative — "your current comercializadora also offers X, which would cost less for your consumption" is a smaller, more defensible claim than cross-provider switching.
- Forces honest framing of any number with "estimado" and visible assumptions.
- The savings claim, when it fires, is high-signal: it's a no-action-required switch within the user's existing customer relationship.

**Negative:**
- Misses the highest-value opportunity. The biggest savings usually come from switching providers, not internal plan changes.
- LLM-based same-comercializadora lookup is non-deterministic. The model may surface outdated or wrong tariff names. Mitigation: always frame the suggestion as "verify on the comercializadora's website" and never quote precise €/kWh figures we can't substantiate.
- Some comercializadoras offer only one plan per modalidad (e.g., small libre players). For those users, the recommendation surface is empty.
