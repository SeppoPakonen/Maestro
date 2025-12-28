# EX-34: Hub Link Generic Cross-Repo Dependency (Beyond U++ Core)

**Scope**: Discover and link packages across local repositories (any build system)
**Outcome**: Explicit cross-repo linking with ambiguity detection and build integration

---

## Preconditions

- Repo truth is JSON under `./docs/maestro/**`
- Multiple repositories on local machine (CMake, U++, Maven, etc.)
- Build system integration active

## Gates / IDs / Stores

- Gates: `REPO_TRUTH_FORMAT_IS_JSON`, `HUB_DETERMINISM`, `HUB_AMBIGUITY_GATE`, `REPOCONF_GATE`
- IDs/cookies/resume tokens: `repo_id` (sha256), `pkg_id` (sha256), `link_id` (sha256:16)
- Stores: `HOME_HUB_INDEX`, `REPO_HUB_LINKS`

---

## Runbook Steps

| Step | Command | Intent | Expected | Gates | Stores |
|------|---------|--------|----------|-------|--------|
| 1 | `maestro repo resolve` | Scan first repo (CoreLib) | Repo model + hub index updated | `REPO_TRUTH_FORMAT_IS_JSON`, `HUB_DETERMINISM` | `REPO_TRUTH_DOCS_MAESTRO`, `HOME_HUB_INDEX` |
| 2 | `maestro repo hub list` | View scanned repos | Shows CoreLib repo in hub | `HOME_HUB_INDEX` | `HOME_HUB_INDEX` |
| 3 | `maestro repo resolve` | Scan second repo (MyApp) | Repo model + hub index updated | `HUB_DETERMINISM` | `REPO_TRUTH_DOCS_MAESTRO`, `HOME_HUB_INDEX` |
| 4 | `maestro repo hub find package CoreLib` | Find CoreLib across repos | Returns single match or ambiguous | `HUB_AMBIGUITY_GATE` | `HOME_HUB_INDEX` |
| 5 | `maestro repo hub link package MyApp --to <PKG_ID>` | Link MyApp to CoreLib | Link created in docs/maestro/repo/hub_links.json | `REPO_TRUTH_FORMAT_IS_JSON` | `REPO_HUB_LINKS` |
| 6 | `maestro repo hub link show` | View current links | Shows MyApp → CoreLib link | none | `REPO_HUB_LINKS` |
| 7 | `maestro make build MyApp` | Build with external link | CoreLib package root added to include paths | `REPOCONF_GATE` | `REPO_TRUTH_DOCS_MAESTRO`, `REPO_HUB_LINKS` |

---

## AI Perspective (Heuristic)

- Use hub linking for cross-repo dependencies (not just U++ nests)
- Always use explicit `--to <PKG_ID>` for ambiguous packages
- Hub index is user-level (`$HOME/.maestro/hub/`), links are repo-local (`./docs/maestro/repo/`)
- Deterministic IDs enable stable references across machines
- Re-scan repos after updates to refresh hub index

---

## Outcomes

### Outcome A: Single Match (Happy Path)

- CoreLib found in exactly one repository
- Link created without ambiguity
- Build succeeds with external package root

### Outcome B: Ambiguous Package

- Multiple CoreLib packages found in different repos
- `maestro repo hub find package CoreLib` returns AMBIGUOUS
- User must use explicit `--to <PKG_ID>` to disambiguate
- Example: `maestro repo hub link package MyApp --to sha256:abc123...`

### Outcome C: Package Not Found

- CoreLib not found in any scanned repository
- `maestro repo hub find package CoreLib` returns NOT_FOUND
- User must scan the containing repository first

---

## Storage Contracts

### Global Hub Index: `$HOME/.maestro/hub/index.json`

```json
{
  "version": "1.0",
  "repos": {
    "sha256:abc123...": {
      "path": "/home/user/repos/CoreLib",
      "last_scanned": "2025-12-29T12:00:00Z",
      "packages_count": 1
    }
  },
  "packages_index": {
    "CoreLib": [
      {"repo_id": "sha256:abc123...", "pkg_id": "sha256:def456..."}
    ]
  }
}
```

### Per-Repo Links: `./docs/maestro/repo/hub_links.json`

```json
{
  "version": "1.0",
  "links": [
    {
      "link_id": "sha256:link123...",
      "from_package": "MyApp",
      "to_package_id": "sha256:def456...",
      "to_package_name": "CoreLib",
      "to_repo_path": "/home/user/repos/CoreLib",
      "created_at": "2025-12-29T13:00:00Z",
      "reason": "explicit"
    }
  ]
}
```

---

## Deterministic Behavior

### Repo ID Formula
```
repo_id = sha256(canonical_path + ":" + git_head + ":" + mtime_summary)
```

### Package ID Formula
```
pkg_id = sha256(build_system + ":" + name + ":" + normalized_path)
```

### Link ID Formula
```
link_id = sha256(from_package + ":" + to_package_id)[:16]  # Truncated to 16 chars
```

---

## CLI Gaps / TODOs

None - all commands implemented.

---

## Trace (YAML)

```yaml
trace:
  example: EX-34
  steps:
    - step: scan_corelib_repo
      command: "cd /home/user/repos/CoreLib && maestro repo resolve"
      gates: [REPO_TRUTH_FORMAT_IS_JSON, HUB_DETERMINISM]
      stores: [REPO_TRUTH_DOCS_MAESTRO, HOME_HUB_INDEX]
    - step: list_scanned_repos
      command: "maestro repo hub list"
      gates: [HOME_HUB_INDEX]
      stores: [HOME_HUB_INDEX]
    - step: scan_myapp_repo
      command: "cd /home/user/repos/MyApp && maestro repo resolve"
      gates: [HUB_DETERMINISM]
      stores: [REPO_TRUTH_DOCS_MAESTRO, HOME_HUB_INDEX]
    - step: find_corelib
      command: "maestro repo hub find package CoreLib"
      gates: [HUB_AMBIGUITY_GATE]
      stores: [HOME_HUB_INDEX]
    - step: link_to_corelib
      command: "maestro repo hub link package MyApp --to sha256:def456..."
      gates: [REPO_TRUTH_FORMAT_IS_JSON]
      stores: [REPO_HUB_LINKS]
    - step: show_links
      command: "maestro repo hub link show"
      gates: []
      stores: [REPO_HUB_LINKS]
    - step: build_with_link
      command: "maestro make build MyApp"
      gates: [REPOCONF_GATE]
      stores: [REPO_TRUTH_DOCS_MAESTRO, REPO_HUB_LINKS]
  stores_considered:
    - REPO_TRUTH_DOCS_MAESTRO
    - HOME_HUB_INDEX
    - REPO_HUB_LINKS
```
