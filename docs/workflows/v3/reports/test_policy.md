# Test Policy

## Runtime Directories

The `docs/maestro/` directory contains runtime state and session data that is specific to individual repo clones.
This directory must NOT be tracked in git as it contains:
- Session state files
- Operation run data
- Convert run artifacts
- Lock files
- Clone-specific metadata

All contents of `docs/maestro/` are considered local runtime state and should be ignored by git.
