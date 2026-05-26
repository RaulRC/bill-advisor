# ADR-0005: PDF-first, Datadis later

**Status:** Accepted

## Context

Two viable input sources exist for analyzing Spanish electricity consumption:

1. **The PDF factura** the customer already receives by email or downloads from their comercializadora's portal. Contains everything that's on the bill — tariff, potencia, kWh per periodo, line-item costs, taxes. No external API or authorization needed.
2. **Datadis** (`datadis.es`) — Spain's official metering portal operated by the distribuidoras. Exposes hourly consumption (curva de carga, CCH) for any CUPS the user authorizes. Richest data source available; required for tariff simulation and time-shifting recommendations.

Datadis requires:
- User OAuth-style authorization via NIF (or pasaporte) + CUPS.
- A registered "empresa autorizada" relationship, or that the integration acts as the user.
- ~3-5 minute onboarding flow including portal account creation if the user doesn't have one.

PDF requires:
- Drag and drop.

For a portfolio MVP targeting "ship something demoable that real people can try in 30 seconds", these are not comparable.

## Decision

Phase 1 ships PDF-only. Datadis integration is documented and deferred to Phase 2.

## Alternatives considered

- **Datadis-only from day one.** Best data, but the onboarding friction would kill demoability and turn any "share this with your friends" moment into "make a Datadis account first." Rejected for Phase 1.
- **Both in parallel.** Doubles the surface area, dilutes focus. Rejected.
- **PDF only forever.** Permanently limits Phase 2 advisor — without hourly data, "shift dishwasher to 03:00" is guesswork. Rejected as a long-term plan but accepted as Phase 1 scope.

## Consequences

**Positive:**
- Zero-friction onboarding. The product works for anyone who has a recent factura PDF, which is everyone with an electricity contract.
- Phase 1 is demoable end-to-end in a single afternoon's worth of build.
- Forces honest framing — without hourly data, we cannot claim "shift X to save Y", which is a healthy constraint.

**Negative:**
- Cannot do hour-aware advice in Phase 1. Suggestions are limited to "potencia contratada parece alta", "tienes alquiler de contador", "estás pagando otros servicios cancelables".
- Cannot accurately simulate alternative tariffs without knowing the user's consumption pattern across hours. Tariff comparator deferred ([ADR-0006](0006-same-comercializadora-only.md)).
- Bill granularity is monthly — patterns within the period (weekday vs weekend, hour of day) are invisible.

## Phase 2 plan

When Datadis lands:
- Tariff simulator runs user's actual hourly consumption against alternative tariffs.
- Time-shifting advisor uses day-ahead price forecasts (from the user's parallel `project_spanish_electricity_forecast` project) to recommend optimal hours for flexible loads.
- Quantified autoconsumo opportunity (how much solar gets vertido vs autoconsumido instantáneamente).
- Optimal potencia contratada recommendation based on P95 of actual peak power.
