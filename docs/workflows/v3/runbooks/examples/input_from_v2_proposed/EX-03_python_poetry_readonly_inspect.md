# EX-03: Python Poetry Read-Only Inspection — No Repo Writes, HOME_HUB_REPO Cache

**Scope**: WF-03 (Read-Only Inspection)
**Build System**: Poetry (Python)
**Languages**: Python 3.11+
**Outcome**: Inspect repo metadata without writing to `./docs/maestro/`, store results in `$HOME/.maestro/hub/repo/`

---

## Scenario Summary

Security auditor inspects a Python Poetry project without modifying repo truth. Maestro detects build system, scans dependencies, identifies entry points, and caches all metadata to `$HOME/.maestro/hub/repo/<repo-id>/`. No issues or tasks are committed to the repo.

---

## Minimal Project Skeleton

```
my-python-api/
├── pyproject.toml
├── poetry.lock
└── src/
    └── api/
        └── main.py
```

**pyproject.toml**:
```toml
[tool.poetry]
name = "my-python-api"
version = "0.2.1"
description = "REST API service"

[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.104.0"
uvicorn = "^0.24.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

**src/api/main.py**:
```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"status": "ok"}
```

---

## Runbook Steps

| Step | Command | Intent | Expected | Gates | Stores |
|------|---------|--------|----------|-------|--------|
| 1 | `maestro repo resolve --no-write` | Scan repo without writes | Detects Poetry, Python 3.11, FastAPI (**hub cache write NOT IMPLEMENTED**; CLI_GAPS: GAP-0001) | REPO_RESOLVE_LITE | HOME_HUB_REPO |
| 2 | `maestro repo pkg list` | Display detected packages | Lists fastapi, uvicorn, Python version | (read-only) | (none) |
| 3 | `maestro repo show --json` | Find executable entry points | **NOT IMPLEMENTED** (CLI_GAPS: GAP-0030) | (read-only) | (none) |

---

## AI Perspective (Heuristic)

**What AI notices:** `pyproject.toml` with Poetry backend → infer Poetry build. No `./docs/maestro/` → read-only mode assumed.

**What AI tries:** Parse `pyproject.toml` for deps, scan `src/` for Python files, cache to `$HOME/.maestro/hub/repo/<hash>/`.

---

## Outcomes

**Outcome A:** Metadata cached successfully, no repo writes.
**Exit:** `$HOME/.maestro/hub/repo/<id>/metadata.json` contains deps, entry points.

**Outcome B:** Incomplete detection → suggests full `maestro init` to enable writes.
**Exit:** Partial metadata cached, warning printed.

---

## CLI Gaps / TODOs

- `maestro repo resolve --no-write` — hub cache write is **NOT IMPLEMENTED** (CLI_GAPS: GAP-0001)
- `maestro repo show --json` — entry point query is **NOT IMPLEMENTED** (CLI_GAPS: GAP-0030)

---

## Trace Block (YAML)

```yaml
trace:
  - user: "maestro repo resolve --no-write"
    intent: "Inspect Python Poetry repo without writes"
    gates: ["REPO_RESOLVE_LITE"]
    stores_write: ["HOME_HUB_REPO"]
    stores_read: []
    internal: ["UNKNOWN"]
    cli_confidence: "medium"

  - user: "maestro repo pkg list"
    intent: "Display detected Python packages"
    gates: []
    stores_read: ["HOME_HUB_REPO"]
    internal: ["UNKNOWN"]
    cli_confidence: "medium"
```

---

**Related:** WF-03
**Status:** Proposed
