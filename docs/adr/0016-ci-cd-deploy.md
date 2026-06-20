# ADR-0016: CI/CD deploy workflow via SSH

**Status:** Accepted
**Date:** 2026-06-13

## Context

The application needed an automated deploy pipeline. Initially the plan was to manually SSH into Lightsail, `git pull`, and `docker build/run` — fragile, error-prone, and a barrier to iteration.

Three approaches were considered:
1. **Manual SSH** — status quo. Works but requires context switching and is easy to forget steps.
2. **GitHub Actions via appleboy/ssh-action** — same SSH commands, automated on every push. Mirror of the existing `raulrc-blog` CI/CD.
3. **GitHub Actions with self-hosted runner on Lightsail** — avoids SSH key management but adds a runner agent to maintain (systemd updates, upgrades, security patches).

## Decision

Use `appleboy/ssh-action` in a GitHub Actions workflow (`.github/workflows/deploy.yml`), same pattern as `raulrc-blog`.

### Deploy steps (executed on Lightsail via SSH)

1. `rm -rf ~/bill-advisor` — clean slate for deterministic builds
2. `git clone` fresh copy via SSH deploy key
3. `docker build -t bill-advisor .` — build the image
4. `docker stop && docker rm` — stop old container (|| true for first deploy)
5. `docker run -d --restart unless-stopped` — start new container with port mapping, env vars, volume mount

### Security

- **SSH key:** The Lightsail instance's public key is registered as a GitHub deploy key (read-only).
- **API keys:** `ANTHROPIC_API_KEY` and `ESIOS_TOKEN` stored as GitHub Secrets, forwarded to the SSH session via `appleboy/ssh-action`'s `envs` parameter, and injected as `-e` flags to `docker run`. The keys never exist in the repository or on disk as files.
- `GITHUB_TOKEN` was initially used for `git clone` but replaced by SSH deploy key due to TTY issues in non-interactive SSH sessions.

## Consequences

**Positive:**
- One-command deploy: push to `main` → live in ~2 minutes.
- Same SSH-based pattern as the blog — no new mental model.
- Zero infrastructure on the CI side — no build caches, no registries, no runners.
- Fresh clone on every deploy eliminates drift from dirty working trees.

**Negative:**
- Full rebuild every time (no layer caching). `pip install` runs from scratch every deploy. Total time ~2 min vs ~30s with caching. Acceptable at current frequency (a few deploys/day max).
- Fresh clone means `docker build` has no cache context — every build downloads all layers. Mitigation: the Layers are cached on the server by Docker's local cache; the build context is fresh but layer reuse works.
- No rollback — if a bad commit ships, you must revert and re-deploy. Acceptable for portfolio.

**Neutral:**
- Triggered on `push: branches: [main]` and `workflow_dispatch` (manual). No scheduled, PR, or tag triggers.
- No test step before deploy. Tests are deferred per ADR-0012.
