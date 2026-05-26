# ADR-0003: Streamlit for the Phase 1 UI

**Status:** Accepted

## Context

Phase 1 needs a UI for two purposes: (a) demoability — a portfolio link the user can share — and (b) a hallucination guardrail, since vision-LLM extractions need a human to spot errors before downstream code trusts the data.

The user's existing stack is Python + Telegram (per other projects: `boebot`, `escalona-bot`). Three UI options were on the table.

## Decision

Build Phase 1 as a Streamlit app (`app.py` at the repo root). Defer Telegram and full web frontend.

## Alternatives considered

- **Telegram bot.** Matches the existing stack, lowest user friction (users send a PDF, bot replies). But harder to demo on a CV ("send a Telegram message to my bot" is awkward), and PDF rendering in Telegram is mediocre. Could be added later as a thin wrapper around the same core extraction + audit modules.
- **Next.js + FastAPI backend.** Most impressive for a portfolio, gives full control over UX. But ~10× the build time for marginal Phase 1 value. Reserved for if the project graduates beyond MVP.
- **Plain CLI only.** Already exists (`python -m bill_advisor.audit <pdf>`). Useful for development, not enough for non-technical users.

## Consequences

**Positive:**
- ~250 lines for a working UI with upload, results, expandable sections.
- Native PDF upload widget via `st.file_uploader`.
- Free deployment on Streamlit Cloud → single shareable portfolio URL.
- Same Python ecosystem — direct imports from `bill_advisor.*`, no API boundary to maintain.
- `@st.cache_data` deduplicates API calls during a session for free.

**Negative:**
- Limited styling control. Streamlit's component aesthetics are recognizable; the UI won't look like a custom product.
- No real authentication or per-user state. Public demos will need a usage cap to avoid API-key drain.
- Single-page architecture is fine for one flow (upload → results) but will get awkward if we add multi-step flows (Datadis auth, multi-bill history, etc.).
- Telegram users (the user's parents, friends) won't have access until we add a Telegram adapter.
