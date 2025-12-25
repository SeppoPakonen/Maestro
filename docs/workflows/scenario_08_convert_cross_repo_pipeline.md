# WF-08: Convert — cross-repo pipeline (New/Plan/Run)

## Metadata

**ID:** WF-08  
**Title:** Convert — cross-repo pipeline (New/Plan/Run)  
**Tags:** [convert, pipeline, export, cross-repo, ast, work-sessions, ai, planning]  
**Entry Conditions:**
- Source repository is resolvable and buildable
- AST is available or generatable from source repo
- Target repository path is specified (new or existing)
- Prerequisites are met (Repo Resolve + RepoConf + AST/TU if required)

**Exit Conditions:**
- Target repository is created/initialized
- Conversion pipeline is executed
- Conversion tasks are written to target repo
- Artifacts are exported to target repo

**Artifacts Created:**
- Pipeline metadata
- AST export
- Task plan in target repo
- Work sessions/transcripts
- Semantic integrity reports
- Conversion memory records

**Failure Semantics:**
- Hard stops: Invalid plan JSON, missing AST, target repo creation failure, semantic integrity violations
- Graceful failures: Individual task failures that don't block the entire pipeline

**Related Commands:**
- `maestro convert new`
- `maestro convert plan`
- `maestro convert run`
- `maestro convert status`
- `maestro convert show`
- `maestro convert reset`

**Links To:**
- WF-05 Repo Resolve
- WF-06 sessions
- WF-07 AST/TU prerequisites

## Two-repo Model (Explicit)

    ### Source vs Target Maestro Instances

    The conversion workflow operates on a two-repository model where the conversion process is initiated from a source repository but executed in/for a separate target repository. This separation is critical for several reasons:

    1. **Prevents Source Repo Contamination:** Conversion output should not be written into the source repository by default, ensuring the original codebase remains pristine.

    2. **Clear Ownership Model:**
       - Source repo owns: AST generation, original code, source-based analysis
       - Target repo owns: new tasks, new code, conversion execution history

    3. **Task/Issue Separation:**
       - Source repo manages: Conversion pipeline initiation, planning, and monitoring
       - Target repo manages: Actual work on conversion tasks, code generation, and verification

    4. **Pipeline Execution:** The conversion is initiated from the source repo but executed in/for the target repo, with tasks being written to the target repository's Track/Phase/Task structure.

    ## Branch Boundaries Note (Cross-Repo Context)

    **Important**: Maestro operates strictly on the current Git branch for both source and target repositories during a conversion pipeline. Switching branches on *either* repository during an active `maestro convert` operation (plan or run) is **unsupported** and risks corrupting the conversion state, leading to inconsistent output or loss of progress. This is an **operational rule**. Users must ensure both source and target repositories are on stable branches before initiating cross-repo conversions.
## Step-by-step Flow

### Step 1: Convert New

The operator runs `maestro convert new [PIPELINE_NAME]` to create a **conversion pipeline instance** with:

- ID/name for the pipeline
- Source repository reference
- Target repository path (new or existing)
- High-level conversion intent (language/framework conversion type)

The operator can list existing pipelines using `maestro convert list` if available.

### Step 2: Convert Plan (AI-assisted)

The operator runs `maestro convert plan <pipeline>` which may initiate an AI discussion to clarify:

- Conversion goals
- Constraints and requirements
- Target structure and organization
- Mechanical vs AI-assisted portions of the conversion

The planning process outputs a **machine-validated final JSON plan** which is a hard stop if invalid. The plan is stored with the pipeline instance and includes:

- Scaffold tasks for project structure
- File conversion tasks
- Final sweep tasks for verification
- Checkpoint policies
- Semantic integrity requirements

### Step 3: Convert Run

The operator runs `maestro convert run <pipeline>` which performs:

1. Ensures prerequisites in source repo (Repo Resolve + RepoConf + AST/TU if required)
2. Generates or loads AST from source repository
3. Exports an AST representation suitable for conversion use
4. Creates/initializes **target repo Maestro instance** (if needed)
5. Writes conversion Tasks into target repo (Track/Phase/Task) representing:
   - Mechanical writes "emit file(s) from AST section X"
   - AI-assisted generation tasks (explicitly labeled)
6. Optionally writes the exported AST into target repo (or references it via path)

After the run, the actual work on tasks happens in the target repo via normal workflows (WF-06 work loop).

## Work Sessions & Transcripts

Convert Plan and Convert Run may create Work Sessions/transcripts that are stored. These Work Sessions leverage file-based polling for IPC, targeted by a `wsession cookie/run-id`, allowing for multi-process operations.

- **Session Ownership:** Transcripts are typically stored in the source repository's docs/maestro/convert directory
- **Recording Types:** Both breadcrumbs (high-level progress) and full stream transcripts (detailed interactions) may be recorded
- **Content:** Includes AI planning discussions, decision-making processes, and execution logs

## Ownership Rules (Must Be Unambiguous)

### Source Repository Owns:
- AST generation and original code
- Source-based analysis
- Conversion planning and pipeline metadata
- Prerequisites (Repo Resolve, RepoConf, AST/TU generation)

### Target Repository Owns:
- New tasks and new code
- Conversion execution history
- Final output artifacts
- Verification and validation results

### Pipeline Metadata:
- May live in source repo or $HOME/.maestro (documented location is docs/maestro/convert/plan/plan.json in the source repo)
- Contains mapping information between source and target files
- Includes coverage maps and conversion status

## Tests Implied by This Scenario

### Unit Tests:
- Pipeline instance creation and listing
- Plan validation (invalid JSON ⇒ stop)
- Run writes target repo structure correctly
- AST export serialization
- Cross-repo path safety (no accidental writes to source)
- Decision override functionality
- Semantic integrity checks

### Integration Tests:
- Fixture source repo with a minimal AST
- Run conversion to a temp target repo
- Verify tasks exist and are parsable in target repo
- Verify pipeline metadata persists and is resumable
- Cross-repo semantic diff functionality
- Playbook constraint enforcement across repos