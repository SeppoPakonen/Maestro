# Multi-Repo Batch Conversions (Batch Mode)

## Overview

Maestro now supports batch mode for running conversions across multiple repositories using shared playbooks, shared baselines, and consistent safety rails. It works like a tour setlist: same conductor, different venues — but no improvisational disasters.

## Batch Spec Format

The batch specification is defined in JSON or YAML format:

```json
{
  "batch_id": "tour_2025_12",
  "description": "Sample batch specification for testing multi-repo conversions", 
  "defaults": {
    "rehearse": true,
    "auto_replan": false,
    "arbitrate": true,
    "max_candidates": 2,
    "judge_engine": "codex",
    "checkpoint_mode": "manual",
    "semantic_strict": true
  },
  "jobs": [
    {
      "name": "repoA_cpp_to_c",
      "source": "/path/to/repoA",
      "target": "/path/to/repoA_out",
      "intent": "high_to_low_level", 
      "playbook": "cpp_to_c",
      "baseline": "optional_baseline_id",
      "tags": ["core", "low_level"]
    },
    {
      "name": "repoB_py_typed",
      "source": "/path/to/repoB", 
      "target": "/path/to/repoB_out",
      "intent": "typedness_upgrade",
      "playbook": null,
      "tags": ["python"]
    }
  ]
}
```

### Schema Validation
- `batch_id`: Required unique identifier for the batch
- `defaults`: Default settings for all jobs in the batch
- `jobs`: Array of job specifications (at least one required)
- Each job requires: `name`, `source`, `target`, and `intent`

## CLI Commands

### Run Batch
```bash
maestro convert batch run --spec batch.json
```

Additional options:
- `--limit-jobs N`: Limit number of jobs to run
- `--only job:job_name`: Run only specific job
- `--only tag:tagname`: Run only jobs with specific tag  
- `--continue-on-error`: Continue when job fails (default: true)
- `--fail-fast`: Stop on first failure (default: false)

### Check Batch Status
```bash
maestro convert batch status --spec batch.json
```

### Show Job Details
```bash
maestro convert batch show --spec batch.json --job repoA_cpp_to_c
```

### Generate Report
```bash
maestro convert batch report --spec batch.json --format json|md|text
```

## Playbook Resolution

Batch mode supports playbook resolution with the following precedence:
1. From explicit path in job spec
2. From repo local `.maestro/playbooks`
3. From user-level `~/.config/maestro/playbooks`
4. From global playbooks

## Checkpoint Handling

Batch mode supports different checkpoint handling modes:
- `manual` (default): Stop job at checkpoint and mark as blocked, continue to next job
- `auto_approve`: Auto-approve checkpoints (only recommended in CI fixtures)
- `fail_on_checkpoint`: Treat any checkpoint as failure (strict CI mode)

These can be set as batch defaults and overridden per job.

## Aggregated Reporting

The batch command generates comprehensive reports including:
- Per-job status (success/failed/interrupted/checkpoint_blocked)
- Last stage reached
- Semantic diff summary (loss counts, top risk flags)
- Checkpoint count and blocking checkpoints
- Drift detection status vs baseline
- Overall totals and failure breakdown
- Worst offenders list (top 5 risk repos)
- Ready to promote list (if rehearsal)

Output formats: JSON (machine-readable), Markdown (human-readable), and text.

## Repository Isolation

Each job maintains per-repo isolation with `.maestro` directories staying per repository. Batch-level logs are stored under `.maestro/batch/<batch_id>/`.

## Error Handling

- Failures in one repository do not corrupt other jobs
- Configurable failure behavior (`--continue-on-error`, `--fail-fast`)
- Detailed error reporting for debugging