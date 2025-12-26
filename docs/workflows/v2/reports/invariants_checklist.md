# Maestro v2 Invariants Checklist

## Overview

This document tracks critical invariants that maintain the integrity and consistency of the Maestro system. These invariants act as a governance spine to prevent architectural drift and ensure compliance with core design principles.

An invariant is a condition that should always hold true in the system. This checklist helps identify when invariants are violated or at risk, enabling proactive maintenance of system integrity.

## Checklist

| Invariant ID | Description | Canonical spec owner | Evidence location | Status | Notes |
|--------------|-------------|---------------------|-------------------|--------|-------|
| REPO_TRUTH_IS_DOCS_MAESTRO | The canonical source of truth for all repository state is maintained in docs/maestro/ | WF-09 | `docs/maestro/` | unknown | |
| REPO_TRUTH_FORMAT_IS_JSON | All repository state is stored in JSON format | WF-09 | `docs/maestro/**/*.json` | unknown | |
| FORBID_REPO_DOT_MAESTRO | Direct access to .maestro directory is forbidden, only docs/maestro/ is allowed | WF-12 | N/A | unknown | |
| HOME_HUB_ALLOWED_IN_READONLY | Home directory hub access is restricted to read-only operations | WF-14 | N/A | unknown | |
| REPO_RESOLVE_IS_DETECTION_SPINE | Repository resolution forms the backbone of dependency detection | WF-15 | N/A | unknown | |
| REPOCONF_REQUIRED_FOR_BUILD_TU_CONVERT | Repository configuration is required for build translation unit conversion | WF-16 | N/A | unknown | |
| BRANCH_SWITCH_FORBIDDEN_DURING_WORK | Branch switching is prohibited during active work sessions | WF-09 | N/A | unknown | |
| WSESSION_COOKIE_REQUIRED | Web session cookies are required for authentication | WF-12 | N/A | unknown | |
| WSESSION_IPC_FILE_BASED | Web session IPC uses file-based communication | WF-14 | N/A | unknown | |
| CONVENTION_ACCEPTANCE_GATE | All changes must pass convention acceptance checks | WF-15 | N/A | unknown | |
| WSESSION_MUTATION_MODE_OPTIN | Web session mutation mode requires explicit opt-in | WF-16 | N/A | unknown | |