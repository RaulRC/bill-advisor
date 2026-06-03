# ADR-0009: PVPC comparator calls ESIOS directly, not via MCP

**Status:** Accepted
**Date:** 2026-06-03

## Context

The project needs hourly PVPC tariff prices (ESIOS indicator #1001) to compare a consumer's fixed-rate bill against the regulated tariff.

Two ESIOS integration options exist:
1. The **spanish-grid-mcp** MCP server (already configured for exploratory queries)
2. A **direct `httpx` call** to the ESIOS API

## Decision

Write a dedicated `pvpc_client.py` that calls ESIOS directly via HTTP.

## Consequences

**Positive:**
- The audit pipeline is self-contained — no dependency on an external MCP server process
- No latency overhead from MCP transport (stdio/IPC)
- The API call can be dependency-injected (accepts optional `esios_token`) for testability without mocking the MCP tool
- Fewer moving parts in CI and deployment

**Negative:**
- Duplicates the ESIOS token and indicator configuration already present in the MCP setup
- Misses future ESIOS indicators that the MCP server might wrap before the direct client does

**Neutral:**
- The MCP server remains useful for exploratory data analysis (generation mix, weather, cross-border flows), but the production pipeline must not depend on it
