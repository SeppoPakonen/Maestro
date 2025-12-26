# EX-04: Ultimate++ Packages — Deep Resolve, Convention Detection, Issues

**Scope**: WF-05 (Ultimate++ Package Scanning)
**Build System**: Ultimate++ (TheIDE, .upp packages)
**Languages**: C++
**Outcome**: Deep repo scan detects `.upp` packages, validates conventions, raises issues for violations

---

## Scenario Summary

Developer working on Ultimate++ codebase runs deep repo resolve. Maestro scans for `.upp` package files, assemblies, detects naming conventions, and creates issues for convention violations (e.g., missing header guards, non-standard package structure).

---

## Minimal Project Skeleton

```
MyU ppApp/
├── MyCore/
│   ├── MyCore.upp
│   ├── Core.h
│   └── Core.cpp
├── MyGui/
│   ├── MyGui.upp
│   ├── Window.h
│   └── Window.cpp
└── MyApp.upp
```

**MyCore/MyCore.upp** (package descriptor):
```
description "Core utilities\n";
uses
    Core;
file
    Core.h,
    Core.cpp;
```

**MyCore/Core.h** (missing header guard - intentional violation):
```cpp
// Missing: #ifndef MYCORE_CORE_H ...
void CoreInit();
```

---

## Runbook Steps

| Step | Command | Intent | Expected | Gates | Stores |
|------|---------|--------|----------|-------|--------|
| 1 | `maestro init` | Initialize Maestro | Creates repo truth | REPOCONF_GATE | REPO_TRUTH_DOCS_MAESTRO |
| 2 | `maestro repo resolve --level deep` | Deep scan for U++ packages | Detects `.upp` files, assemblies | REPO_RESOLVE_DEEP | REPO_TRUTH_DOCS_MAESTRO |
| 3 | `TODO_CMD: maestro repo show packages` | List detected packages | Shows MyCore, MyGui, MyApp | (read-only) | (none) |
| 4 | `TODO_CMD: maestro repo conventions check` | Validate U++ conventions | Detects missing header guards | CONVENTIONS_GATE | REPO_TRUTH_DOCS_MAESTRO (issues) |
| 5 | `TODO_CMD: maestro issues list --type convention` | Show convention issues | Lists "Missing header guard in MyCore/Core.h" | (read-only) | (none) |
| 6 | `TODO_CMD: maestro issues accept <issue-id>` | Accept issue for fixing | Issue status → `accepted` | REPOCONF_GATE | REPO_TRUTH_DOCS_MAESTRO |

---

## AI Perspective (Heuristic)

**What AI notices:** `.upp` files → Ultimate++ project. Standard convention: header guards with `PACKAGE_FILE_H` pattern.

**What AI tries:** Scan all `.h` files, check for `#ifndef` guards, match against package/file name pattern.

---

## Outcomes

**Outcome A:** Conventions detected, violations create issues, user accepts.
**Exit:** Issues documented in `./docs/maestro/issues/`, user fixes or ignores.

**Outcome B:** Conventions accepted as-is, no violations.
**Exit:** Convention acceptance gate passed, no issues created.

---

## CLI Gaps / TODOs

- `TODO_CMD: maestro repo show packages` — U++ package listing
- `TODO_CMD: maestro repo conventions check` — convention validation command
- `TODO_CMD: maestro issues list --type convention` — filter by type
- `TODO_CMD: maestro issues accept <id>` — acceptance workflow

---

## Trace Block (YAML)

```yaml
trace:
  - user: "maestro repo resolve --level deep"
    intent: "Deep scan for Ultimate++ packages and assemblies"
    gates: ["REPO_RESOLVE_DEEP"]
    stores_write: ["REPO_TRUTH_DOCS_MAESTRO"]
    internal: ["UNKNOWN"]
    cli_confidence: "medium"

  - user: "maestro repo conventions check"
    intent: "Validate U++ naming and structure conventions"
    gates: ["CONVENTIONS_GATE"]
    stores_write: ["REPO_TRUTH_DOCS_MAESTRO"]  # creates issues
    internal: ["UNKNOWN"]
    cli_confidence: "low"  # TODO_CMD
```

---

**Related:** WF-05
**Status:** Proposed
