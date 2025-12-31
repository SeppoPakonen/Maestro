# EX-39: BatchScriptShell Phase 0.5 Build→Log→Issues Runbook

## Overview
This runbook demonstrates the BatchScriptShell Phase 0.5 workflow: isolated build, log scanning, issue ingestion, and triage using the Maestro observability pipeline.

## Prerequisites
- BatchScriptShell repository at `~/Dev/BatchScriptShell`
- Maestro repository at `~/Dev/Maestro`
- CMake and build tools installed
- MAESTRO_DOCS_ROOT environment variable support

## Success Criteria
- BatchScriptShell repo model is verified (assemblies/packages correctly wired)
- Isolated build produces logs
- Log scan produces stable fingerprints
- Issues are ingested and deduplicated properly
- Issues are automatically triaged with appropriate severities

## Steps

### 1. Verify Repository Model
```bash
cd ~/Dev/BatchScriptShell
MAESTRO_DOCS_ROOT="./docs/maestro" python3 ~/Dev/Maestro/maestro.py repo resolve -v
MAESTRO_DOCS_ROOT="./docs/maestro" python3 ~/Dev/Maestro/maestro.py repo asm list
MAESTRO_DOCS_ROOT="./docs/maestro" python3 ~/Dev/Maestro/maestro.py repo pkg
```

Expected output:
- One `bss` package with build_system `multi` (cmake+autoconf)
- Virtual packages exist (docs-*, tests-*, scripts-*)
- Virtual packages are routed to matching assemblies
- Root assembly contains only non-virtual packages (primarily `bss`)

### 2. Create Isolated Build
```bash
cd ~/Dev/BatchScriptShell
rm -rf build_maestro && mkdir -p build_maestro
cd build_maestro
cmake .. 2>&1 | tee /tmp/bss_cmake_configure.log
cmake --build . 2>&1 | tee /tmp/bss_cmake_build.log
```

### 3. Generate Error Log (for demonstration)
```bash
# Add intentional error to source file
cd ~/Dev/BatchScriptShell
echo "int intentional_error_function() { int x = ; return 0; }" >> shell.c

# Rebuild to generate errors
cd ~/Dev/BatchScriptShell/build_maestro
cmake --build . 2>&1 | tee /tmp/bss_cmake_build_with_errors.log
```

### 4. Log Scan → Issues Ingestion → Triage
```bash
# Scan the build log with errors
cd ~/Dev/BatchScriptShell
cat /tmp/bss_cmake_build_with_errors.log | MAESTRO_DOCS_ROOT="./docs/maestro" python3 ~/Dev/Maestro/maestro.py log scan --stdin --kind build

# Capture the SCAN_ID from the output (format: YYYYMMDD_HHMMSS_build)
# Example: 20260101_012925_build

# Ingest issues from the scan
MAESTRO_DOCS_ROOT="./docs/maestro" python3 ~/Dev/Maestro/maestro.py issues add --from-log <SCAN_ID>

# Auto-triage the issues
MAESTRO_DOCS_ROOT="./docs/maestro" python3 ~/Dev/Maestro/maestro.py issues triage --auto

# List the created issues
MAESTRO_DOCS_ROOT="./docs/maestro" python3 ~/Dev/Maestro/maestro.py issues list --status open
```

### 5. Verify Determinism and Deduplication
```bash
# Scan the same log again to test determinism
cat /tmp/bss_cmake_build_with_errors.log | MAESTRO_DOCS_ROOT="./docs/maestro" python3 ~/Dev/Maestro/maestro.py log scan --stdin --kind build

# Ingest issues again to verify deduplication
MAESTRO_DOCS_ROOT="./docs/maestro" python3 ~/Dev/Maestro/maestro.py issues add --from-log <NEW_SCAN_ID>

# Check that no duplicate issues were created
MAESTRO_DOCS_ROOT="./docs/maestro" python3 ~/Dev/Maestro/maestro.py issues list --status open
```

Expected: Same number of issues as before (no duplicates created)

## Notes
- Build failures are acceptable and generate issues for analysis
- SCAN_ID format: YYYYMMDD_HHMMSS_build
- Issue deduplication works based on stable fingerprints
- Deterministic fingerprints ensure same log produces same scan results