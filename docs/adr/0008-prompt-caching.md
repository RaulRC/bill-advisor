# ADR-0008: Prompt caching strategy

**Status:** Accepted

## Context

Each PDF extraction sends:
- A large system prompt (~3000 tokens of Spanish electricity domain knowledge)
- The `Factura` Pydantic JSON schema, serialized into the tool definition (~2100 tokens)
- The PDF document block (variable, ~1-3K tokens)
- A short user instruction (~100 tokens)

The first three components account for the vast majority of input tokens. The system prompt and tool schema are *stable* — they don't change between extractions. Anthropic's prompt caching offers ~90% cost reduction on cached prefixes and ~80% latency reduction.

Caching is a prefix match: any byte change anywhere in the prefix invalidates everything after it. Render order is `tools → system → messages`.

Opus models require a minimum cacheable prefix of **4096 tokens**; below that, `cache_control` markers silently no-op (no error, just zero cache hits).

## Decision

Mark the last system text block with `cache_control: {type: "ephemeral"}`. This caches both the tool schema (rendered earlier) and the system prompt together as one prefix block. The PDF + short user instruction (which vary per request) sit after the cache boundary and are processed fresh.

Combined cacheable prefix is ~5192 tokens — comfortably above the 4096 Opus minimum.

## Alternatives considered

- **Top-level auto-caching (`cache_control` directly on `messages.create()`).** Simpler but less explicit about *where* the cache boundary sits. Rejected for clarity.
- **No caching.** Loses ~90% of input-token cost on repeated extractions. Rejected.
- **Cache the PDF too** via the Files API (upload once, reference by file_id). Useful if a single user uploads the same PDF many times, but in our use case each upload is a different bill. Rejected for Phase 1.
- **Trim the system prompt below the Opus minimum and skip caching.** Would simplify the prompt but lose the rich extraction quality (the prompt's glossary of comercializadoras, distribuidoras, modalidades, and impuesto rules genuinely drives accuracy). Rejected.

## Consequences

**Positive:**
- Second and subsequent extractions in a 5-minute window read the cached prefix at ~0.1× cost — meaningful savings for any session involving multiple bills (e.g., demo sessions, batch reprocessing during development).
- ~80% latency reduction on cached requests.
- The cache_control marker is also an explicit boundary documenting "everything above this is stable input."

**Negative:**
- The cache silently no-ops if the prefix falls below 4096 tokens. Future prompt simplification work must check this — `len(SYSTEM_PROMPT + Factura.model_json_schema()) >= ~4096 tokens` is now a hidden constraint.
- Any change to the system prompt or the `Factura` schema invalidates the entire cache and forces the next request to re-write it (1.25× cost on write).
- 5-minute ephemeral TTL means caching only helps within a session, not across cold starts. Acceptable for our use pattern.
- Verification requires inspecting `response.usage.cache_read_input_tokens` — currently not exposed in the UI. Cache hit telemetry is on the [next-steps list](../next-steps.md) §2.
