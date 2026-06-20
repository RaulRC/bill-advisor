# ADR-0017: Secrets management — no .env in production

**Status:** Accepted
**Date:** 2026-06-13

## Context

The application requires two API keys at runtime: `ANTHROPIC_API_KEY` (for LLM extraction and RAG chat) and `ESIOS_TOKEN` (for PVPC tariff comparison). These must be available inside the Docker container but must never be committed to the repository.

Three approaches were considered:
1. **`.env` file on the server** — `scp .env` or `nano .env` during initial setup, then `--env-file .env` to `docker run`. Simple but creates a persistent credential file on disk.
2. **GitHub Secrets + `-e` flags** — store keys in GitHub Actions Secrets, forward via `appleboy/ssh-action`'s `envs` parameter, pass as `-e VAR="$VAR"` to `docker run`. No credentials on disk.
3. **Secrets manager (AWS Secrets Manager / Parameter Store)** — auditable, rotated, but adds AWS costs and a dependency. Over-engineered for a portfolio app.

## Decision

Use **GitHub Secrets + `-e` flags** (option 2).

The deploy workflow forwards the secrets to the SSH session:

```yaml
- uses: appleboy/ssh-action@v1
  with:
    envs: ANTHROPIC_API_KEY,ESIOS_TOKEN
    ...
  env:
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
    ESIOS_TOKEN: ${{ secrets.ESIOS_TOKEN }}
```

The remote script then injects them directly:

```bash
docker run ... \
  -e ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  -e ESIOS_TOKEN="$ESIOS_TOKEN" \
  ...
```

For **local development**, `.env` is still used (loaded by `python-dotenv` via `load_dotenv()`). The `.env` file is in `.gitignore` and `.dockerignore`.

## Consequences

**Positive:**
- No credential files on the server — keys exist only in memory during the container's lifetime.
- No risk of accidentally committing keys to the repository.
- Rotation is simple: update the GitHub Secret and re-deploy.
- Same pattern for both keys — uniform handling.

**Negative:**
- Keys are visible in the process list inside the container (`ps aux` shows `-e ANTHROPIC_API_KEY=...`). Acceptable for a single-user portfolio app.
- If the container crashes, the keys are gone — no .env file to restart from. Mitigation: `--restart unless-stopped` ensures the container restarts automatically via the deploy workflow (the workflow re-runs `docker run` with the same env vars).
- Local dev requires a .env file — the two workflows are intentionally different.

**Neutral:**
- The `appleboy/ssh-action` `envs` parameter forwards any environment variable from the runner to the SSH session. The `env` block at the step level sets these from secrets.
- `GITHUB_TOKEN` was initially used for git clone auth but replaced with an SSH deploy key — the token's `$` characters caused issues in non-TTY SSH sessions.
