# ADR-0007: Flat package layout (`bill_advisor/`, not `src/`)

**Status:** Accepted

## Context

The initial repo scaffold used `src/schemas.py`, `src/extraction.py`, etc. — a "flat src" layout that uses a directory literally named `src` as the package name. This means imports read `from src.schemas import Factura`, which:

- Leaks repo structure into the import path (callers shouldn't care that the source is under `src/`).
- Conflicts with the standard "src-layout" convention (`src/<packagename>/...`) used by libraries.
- Reads oddly when `src` becomes the visible namespace in tracebacks and tooling.

## Decision

Move the package to the repo root as `bill_advisor/`. Imports become `from bill_advisor.schemas import Factura`. Configure Hatchling in `pyproject.toml` to package `bill_advisor`:

```toml
[tool.hatch.build.targets.wheel]
packages = ["bill_advisor"]
```

## Alternatives considered

- **src-layout (`src/bill_advisor/`).** Standard for libraries. More robust against accidental imports during development. Slightly more friction for a Streamlit app (the entry point and the package live at different levels). Acceptable but not chosen — for a single-app project, the flat layout has lower cognitive overhead.
- **Keep `src/` as the package name.** Anti-pattern. Rejected.
- **No package, just `schemas.py` and `extraction.py` at the root.** Fine for one-off scripts; breaks when modules want to import each other and the project grows past 3-4 files.

## Consequences

**Positive:**
- Clean, readable imports throughout — `from bill_advisor.audit import audit` matches what a reader expects.
- Streamlit entry point (`app.py`) and the package live at the same level, so the run command stays simple.

**Negative:**
- Marginally less robust than src-layout against accidental "I imported the local copy, not the installed one" bugs. In practice, with `uv pip install -e .` and a clean venv this hasn't been an issue.
- If the project ever extracts a library (e.g., publishing `bill_advisor` as a PyPI package separate from the Streamlit app), migrating to src-layout would be a small one-time refactor.
