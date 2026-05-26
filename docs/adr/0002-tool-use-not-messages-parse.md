# ADR-0002: Use tool use, not `messages.parse`, for structured output

**Status:** Accepted

## Context

The initial implementation used `client.messages.parse(output_format=Factura)` — the modern Anthropic SDK shortcut for Pydantic-validated structured output. Under the hood this compiles a strict grammar from the Pydantic JSON schema on the server side, guaranteeing schema-compliant output.

When the schema grew to include the PVPC sub-block ([ADR-0004](0004-pvpc-sub-block-schema.md)) and the bono social financing field, the API started returning:

```
400: The compiled grammar is too large, which would cause performance issues.
Simplify your tool schemas or reduce the number of strict tools.
```

The cause: the constrained-grammar compiler is sensitive to *grammar complexity*, not raw token size. The `Factura` schema has ~15 `Optional[X]` fields (each compiles to `anyOf [type, null]`) across 6+ nested models. The combinatorial expansion exceeded the server-side compiler's limit.

## Decision

Drop down from `client.messages.parse()` to plain `client.messages.create()` with a single tool definition `record_factura_extraida` whose `input_schema` is `Factura.model_json_schema()`. Force the tool's invocation with `tool_choice={"type": "tool", "name": "record_factura_extraida"}`. Pydantic validates the tool_use input client-side after the response returns.

## Alternatives considered

- **Reduce `Optional` field count in the schema.** Would force lossy choices — "not present" vs "zero" would collapse into the same value, breaking audit checks that distinguish "you don't pay a contador rental" from "you pay zero euros for a contador rental".
- **Flatten the schema by inlining nested models.** Lose the schema's economic-meaning separation (peajes vs mercado mayorista vs margen).
- **Use `output_config.format` with raw JSON schema and `strict: true`.** Same grammar-compiler issue.
- **Drop `strict: true` but stay in `output_config.format`.** This was actually the closest alternative. We chose tool use because it makes the contract more explicit ("the model must call this tool with this shape") and matches the user's original mental model of how this should work.

## Consequences

**Positive:**
- Schema can grow as bills get more complex (autoconsumo modalities, 3.0TD tariffs, surplus compensation tiers, etc.) without hitting a server-side limit.
- Same correctness guarantee in practice: `tool_choice` forces the model to call the tool exactly once with the schema-shaped JSON.
- Pydantic still validates client-side; invalid input raises `ValidationError`, surfaced to the user.
- More transparent — the API call is explicit about the contract.

**Negative:**
- Slightly more boilerplate vs `output_format=Factura` (manual tool definition + tool_use extraction + Pydantic validation step).
- No server-side validation; if the model produces malformed JSON, we discover it only after the round trip. Rare in practice with Opus.
- Manual handling of `stop_reason == "refusal"` and missing-tool-use edge cases.
