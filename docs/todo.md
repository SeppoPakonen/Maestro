# Maestro Development TODO

> **Planning Document**: Comprehensive roadmap for Maestro development, covering AI-powered development workflow, repository analysis, issues management, and universal build system integration.

**Last Updated**: 2025-12-20 (Phase RF2: Repository Hierarchy Analysis completed)

---

## Table of Contents

### Legend
- ✅ **Done**: Completed and tested
- 🚧 **In Progress**: Currently being worked on
- 📋 **Planned**: Specified and scheduled
- 💡 **Proposed**: Concept stage, needs refinement
- ⚠️ **Deprecated**: Scheduled for removal or replacement

### Current Status Overview

| Track | Phase | Status | Completion |
|-------|-------|--------|------------|
| **🔥 Repository Foundation** | | | |
| | RF1: Init & Resolve | ✅ Done | 100% |
| | RF2: Repository Hierarchy Analysis | ✅ Done | 100% |
| | RF3: Convention Detection | 📋 Planned | 0% |
| | RF4: Repository Rules | 🚧 In Progress | 66% |
| | RF5: Refresh All | ✅ Done | 100% |
| **Build & Run** | | | |
| | BR1: Make Integration with Issues | 📋 Planned | 0% |
| | BR2: Static Analyzer Integration | 📋 Planned | 0% |
| | BR3: Run Command | 📋 Planned | 0% |
| | BR4: Profiling Support | 📋 Planned | 0% |
| **Issues & Solutions** | | | |
| | IS1: Issue Data Model | 📋 Planned | 0% |
| | IS2: Issue Categories | 📋 Planned | 0% |
| | IS3: Issue 4-Phase Workflow | 📋 Planned | 0% |
| | IS4: Solutions System | 📋 Planned | 0% |
| | IS5: Runtime Issue Collection | 💡 Proposed | 0% |
| **Work & Session Framework** | | | |
| | WS1: Session Infrastructure | 📋 Planned | 0% |
| | WS2: Breadcrumb System | 📋 Planned | 0% |
| | WS3: Work Command | 📋 Planned | 0% |
| | WS4: Session Visualization | 📋 Planned | 0% |
| | WS5: Migrate CLI Discussions | 📋 Planned | 0% |
| **Observability** | | | |
| | OB1: Hub System | 📋 Planned | 0% |
| | OB2: Log System | 📋 Planned | 0% |
| | OB3: Global Repo Index | 📋 Planned | 0% |
| **Code Transformation** | | | |
| | CT1: TU/AST for Issue Fixing | 📋 Planned | 0% |
| | CT2: Conversion Pipeline | 📋 Planned | 0% |
| | CT3: Multi-language Convert | 💡 Proposed | 0% |
| **Cleanup & Migration** | | | |
| | CM1: Remove Deprecated Commands | 📋 Planned | 0% |
| | CM2: Rename Settings File | 📋 Planned | 0% |
| | CM3: Update Help System | 📋 Planned | 0% |
| **🔥 Track/Phase/Task CLI** | | | |
| | CLI1: Markdown Data Backend | ✅ Done | 100% |
| | CLI2: Track/Phase/Task Commands | ✅ Done | 100% |
| | CLI3: AI Discussion System | ⚠️ Deprecated | 100% |
| | CLI4: Settings and Configuration | ⚠️ Needs Migration | 100% |
| | CLI5: TUI Conversion | ✅ Done | 100% |
| **UMK Integration** | | | |
| | Phase 1-11 | 📋 Planned | varies |
| | Phase 12: Retroactive Fixes | 🚧 In Progress | 10% |
| **TU/AST System** | | | |
| | TU1-TU7 | ✅ Done | 100% |
| **Test Meaningfulness** | | | |
| | TM1: Test Audit | 📋 Planned | 0% |

---

## 🔥 Track: Repository Foundation

"track_id": "repo-foundation"
"priority": 0
"status": "planned"
"completion": 0%

This track implements the foundational repository analysis and management commands that users interact with first when working with a codebase. Integrates the completed assembly detection system (Phase AS1) into repository hierarchy analysis.

**Command Hierarchy**:
- `maestro init` - Initialize Maestro in a repository
- `maestro repo resolve` - Scan and identify packages, build systems, assemblies
- `maestro repo refresh all` - Full refresh (resolve + conventions + rules analysis)
- `maestro repo refresh help` - Show what refresh all does
- `maestro repo hier` - Show AI-analyzed repository hierarchy
- `maestro repo pkg <id> --show-groups` - Show internal package groups (from Phase 11)
- `maestro repo pkg <id> --group <group>` - Show specific group (from Phase 11)
- `maestro repo conventions` - Show/edit detected conventions
- `maestro repo conventions detect` - Explicitly detect conventions
- `maestro repo rules` - Show/edit repository rules

### Phase RF1: Init & Resolve ✅ **[Completed 2025-12-20]**

"phase_id": "rf1"
"status": "done"
"completion": 100

- [x] **RF1.1: Maestro Init Command** ✅
  - Initialize `.git`-relative Maestro workspace
  - Create `docs/` directory structure
  - Initialize `docs/Settings.md` (renamed from config.md)
  - Initialize `docs/RepoRules.md`
  - Create `docs/sessions/` directory
  - Create `docs/issues/` directory
  - Create `docs/solutions/` directory
  - Update `$HOME/.maestro/` global index

- [x] **RF1.2: Repository Resolve** ✅ (Already implemented)
  - Scan for packages (U++, CMake, Autotools, Maven, Gradle, etc.)
  - Detect build systems
  - Identify assemblies (U++, custom) - ✅ Infrastructure exists from Phase AS1
  - Create repository metadata
  - Integration with existing package scanners
  - Integration with completed assembly detection system

### Phase RF2: Repository Hierarchy Analysis ✅ **[Completed 2025-12-20]**

"phase_id": "rf2"
"status": "done"
"completion": 100

- [x] **RF2.1: Hierarchy Detection** ✅
  - AI-powered analysis of directory structure ✅
  - Identify logical groupings (not just filesystem) ✅
  - Detect package groups ✅
  - Recognize assemblies and their structure - ✅ Assembly system from Phase AS1
  - Map relationships between components ✅
  - Leverage completed assembly detection infrastructure ✅
  - **Internal Package Groups** (from UMK Phase 11):
    - Parse U++ separators (Core/Core.upp structure) ✅
    - Auto-group misc packages by file type (docs, scripts, build files) ✅
    - Create FileGroup representation in package metadata ✅

- [x] **RF2.2: Hierarchy Visualization** ✅
  - Tree-view terminal output ✅
  - Show packages, assemblies, groups - ✅ Assembly data available from Phase AS1
  - Hierarchical display of build systems ✅
  - Color-coded output ✅
  - Export to JSON format ✅
  - Display assembly relationships and package organization ✅
  - **Internal Package Groups Display** (from UMK Phase 11):
    - CLI: `maestro repo hier` - Show hierarchy ✅
    - CLI: `maestro repo hier --show-files` - Show file groups ✅
    - CLI: `maestro repo hier --json` - JSON output ✅
    - CLI: `maestro repo hier --rebuild` - Force rebuild ✅
    - Display group headers with file counts ✅
    - Collapsible/expanded view (via --show-files flag) ✅

- [x] **RF2.3: Hierarchy Editing** ✅
  - Manual hierarchy overrides ✅ (.maestro/repo/hierarchy_overrides.json)
  - CLI: `maestro repo hier edit` - Edit overrides in $EDITOR ✅
  - Persistent hierarchy storage ✅ (.maestro/repo/hierarchy.json)
  - Override merge system ✅

## Deliverables:
- ✅ Hierarchy detection from repository scan results
- ✅ Tree visualization with colors and symbols
- ✅ JSON export support
- ✅ File group display support
- ✅ Hierarchy override system
- ✅ CLI: `maestro repo hier [show]` - Display hierarchy
- ✅ CLI: `maestro repo hier edit` - Edit overrides
- ✅ Storage: `.maestro/repo/hierarchy.json`
- ✅ Storage: `.maestro/repo/hierarchy_overrides.json`

## Test Criteria:
- ✅ Hierarchy correctly represents repository structure
- ✅ Tree output is readable with proper indentation
- ✅ Colors and symbols enhance readability
- ✅ JSON output is valid and complete
- ✅ File groups display correctly with --show-files
- ✅ Override system works as expected
- ✅ All commands execute without errors

## Success Metrics:
- ✅ All three RF2 tasks completed
- ✅ Hierarchy visualization provides clear overview
- ✅ JSON export enables programmatic access
- ✅ Override system allows manual customization
- ✅ All test criteria met

### Phase RF3: Convention Detection

"phase_id": "rf3"
"status": "planned"
"completion": 0

- [ ] **RF3.1: Convention Detection Engine**
  - Auto-detect naming conventions (CapitalCase, snake_case, UPPER_CASE)
  - Detect file organization patterns
  - Identify include/import patterns
  - Framework-specific conventions (U++, Qt, etc.)
  - Language-specific conventions (C++, Java, Python)

- [ ] **RF3.2: Convention Rulesets**
  - U++ conventions: CapitalCase classes/functions, underscore_case variables, UPPER_CASE enums
  - Autotools + STL conventions
  - Java conventions
  - Python conventions (PEP 8)
  - Custom convention definitions

- [ ] **RF3.3: Convention Storage & Editing**
  - Store conventions in `docs/RepoRules.md`
  - Structured markdown format (## Convention + key: value lists)
  - Fields: `variable_name`, `function_name`, `class_name`, `enum_name`
  - Fields: `include_allowed_in_all_headers`, `use_primary_header`, `include_primary_header_in_impl`
  - Manual editing support
  - AI-assisted convention refinement

### Phase RF4: Repository Rules

"phase_id": "rf4"
"status": "in_progress"
"completion": 66

- [x] **RF4.1: Rule Storage System** ✅
  - `docs/RepoRules.md` structured markdown
  - Sections for different rule types
  - Natural language rules (for AI injection)
  - JSON-formatted rule metadata

- [x] **RF4.2: Rule Management Commands** ✅ (Partially implemented)
  - `maestro repo rules` - Show current rules ✅
  - `maestro repo rules edit` - Edit rules in $EDITOR ✅
  - `maestro repo rules add <category>` - Add new rule (future)
  - AI-assisted rule extraction from discussions (future)

- [ ] **RF4.3: Rule Application** (Phase not yet started)
  - Inject rules into AI prompts based on context
  - Rule categories: architecture, security, performance, style
  - Context-aware rule selection

### Phase RF5: Refresh All ✅ **[Completed 2025-12-20]**

"phase_id": "rf5"
"status": "done"
"completion": 100

- [x] **RF5.1: Refresh All Implementation** ✅
  - Execute `repo resolve` ✅
  - Execute `repo conventions detect` (placeholder - Phase RF3)
  - Execute `repo hier` analysis (placeholder - Phase RF2)
  - Update all caches and indices ✅
  - Incremental refresh support (future)

- [x] **RF5.2: Refresh Help** ✅
  - `repo refresh help` - Show all steps in order ✅
  - Document what each step does ✅
  - Show estimated time for each step (future)

---

## Track: Build & Run

"track_id": "build-run"
"priority": 1
"status": "planned"
"completion": 0%

This track implements the build and execution commands, with integrated issue tracking for build errors.

**Command Hierarchy**:
- `maestro make` - Build the project (replaces old `build` command)
- `maestro make <package>` - Build specific package
- `maestro make <package> <config>` - Build with specific config
- `maestro make <package> --group <group>` - Build specific internal group (from Phase 11)
- `maestro run` - List packages and mainconfigs
- `maestro run <package> <mainconfig>` - Execute built binary
- `maestro run <package> <mainconfig> --profile [args...]` - Run with profiler
- `maestro repo pkg <id> run <mainconfig>` - Alternative syntax
- `maestro repo pkg <id> profile <mainconfig>` - Alternative syntax

### Phase BR1: Make Integration with Issues

"phase_id": "br1"
"status": "planned"
"completion": 0

- [ ] **BR1.1: Make Command Implementation**
  - Replace deprecated `build` command
  - Integrate with UMK builder system
  - Support package-specific builds
  - Support build configuration selection
  - **Group-Specific Builds** (from UMK Phase 11):
    - `maestro make <package> --group <group>` - Build specific group only
    - Platform-specific group builds (e.g., build only Win32 group)
    - Dependency tracking per group

- [ ] **BR1.2: Build Error Detection**
  - Parse compiler errors (gcc, clang, msvc, javac, etc.)
  - Parse linker errors
  - Extract error location (file:line:column)
  - Extract error messages

- [ ] **BR1.3: Automatic Issue Creation**
  - Create issues from build errors
  - Issue type: `build`
  - Auto-generate issue ID (hash-based)
  - Store in `docs/issues/<issue-id>.md`
  - Link to source location

- [ ] **BR1.4: Build Error UI Flow**
  - Show build errors in terminal
  - Prompt: "Fix build errors automatically? (y/n)"
  - If yes: trigger `work issue <id>` for each error
  - If no: just list issues for later

### Phase BR2: Static Analyzer Integration

"phase_id": "br2"
"status": "planned"
"completion": 0

- [ ] **BR2.1: Static Analyzer Support**
  - Integrate clang-tidy (C++)
  - Integrate cppcheck (C++)
  - Integrate pylint (Python)
  - Integrate checkstyle (Java)
  - Configurable analyzer selection

- [ ] **BR2.2: Analyzer Error to Issue**
  - Parse static analysis warnings/errors
  - Create issues with type: `convention` or `build`
  - Include analyzer name and rule in issue metadata
  - Link to documentation for rule violations

### Phase BR3: Run Command

"phase_id": "br3"
"status": "planned"
"completion": 0

- [ ] **BR3.1: Run Package Discovery**
  - List all buildable packages
  - Identify executable outputs
  - List available mainconfigs per package
  - Show build status (built/not built/out of date)

- [ ] **BR3.2: Run Execution**
  - Execute built binaries
  - Pass arguments to binary
  - Capture stdout/stderr
  - Report exit codes
  - Handle crashes gracefully

- [ ] **BR3.3: Run Integration with Issues**
  - Monitor for crashes
  - Detect assertion failures
  - Capture exception traces
  - Create runtime issues automatically

### Phase BR4: Profiling Support

"phase_id": "br4"
"status": "planned"
"completion": 0

- [ ] **BR4.1: Profiler Integration**
  - Support for gprof (C++)
  - Support for valgrind (memory profiling)
  - Support for perf (Linux)
  - Support for Java profilers (YourKit, VisualVM)
  - Support for Python profilers (cProfile)

- [ ] **BR4.2: Profiling Output**
  - Generate profiling reports
  - Store in `docs/profiling/<package>-<timestamp>.md`
  - Visualize hotspots
  - Detect performance regressions

---

## Track: Issues & Solutions

"track_id": "issues-solutions"
"priority": 2
"status": "planned"
"completion": 0%

This track implements the comprehensive issue tracking and solution management system.

**Command Hierarchy**:
- `maestro issues` - List all issues
- `maestro issues hier` - Hierarchy issues (files in wrong places)
- `maestro issues convention` - Convention violations
- `maestro issues build` - Build/compilation errors
- `maestro issues runtime` - Runtime errors (crashes, exceptions)
- `maestro issues features` - Feature requests/UX issues
- `maestro issues product` - Product direction issues
- `maestro issues look` - Visual/aesthetic issues
- `maestro issues ux` - User experience issues
- `maestro issues show <id>` - Show issue details
- `maestro issues fix <id>` - Start fixing an issue
- `maestro solutions` - List all known solutions
- `maestro solutions add` - Add new solution (AI discussion)
- `maestro solutions remove <id>` - Remove solution
- `maestro solutions list` - List solutions

### Phase IS1: Issue Data Model

"phase_id": "is1"
"status": "planned"
"completion": 0

- [ ] **IS1.1: Issue Schema**
  - Issue ID: auto-generated hash or semantic ID
  - Issue type: hier/convention/build/runtime/features/product/look/ux
  - Issue state: open/reacted/analyzing/analyzed/decided/fixing/fixed/closed/cancelled
  - Priority: 0-100 (0 = most important)
  - Title: optional user-provided title
  - Description: error message or user description
  - Location: file:line:column (if applicable)
  - Created: timestamp
  - Modified: timestamp
  - Related track/phase: optional link

- [ ] **IS1.2: Issue Storage**
  - Store as `docs/issues/<issue-id>.md`
  - Structured markdown format
  - JSON metadata block
  - Human-readable content
  - Version control friendly

- [ ] **IS1.3: Issue Lifecycle**
  - State machine: open → reacted → analyzing → analyzed → decided → fixing → fixed → closed
  - State transitions logged with timestamps
  - Auto-save state changes
  - Support for state rollback

### Phase IS2: Issue Categories

"phase_id": "is2"
"status": "planned"
"completion": 0

- [ ] **IS2.1: Hierarchy Issues**
  - Files in wrong directories
  - Incorrect package organization
  - Assembly structure violations
  - Detected by `repo hier` analysis

- [ ] **IS2.2: Convention Issues**
  - Naming convention violations
  - Style guide violations
  - Detected by convention checking
  - Framework-specific convention violations (U++)

- [ ] **IS2.3: Build Issues**
  - Compilation errors (gcc, clang, msvc, javac)
  - Linker errors
  - Detected automatically during `make`
  - Temporary issues (hash-based ID)

- [ ] **IS2.4: Runtime Issues**
  - Crashes (segfaults, exceptions)
  - Failed assertions
  - Warnings logged to monitoring system
  - Requires instrumentation (future phase)

- [ ] **IS2.5: Features/UX Issues**
  - User-reported issues
  - Developer-identified issues
  - Manual creation only
  - Can have descriptive titles

- [ ] **IS2.6: Product/Look Issues**
  - High-level product direction
  - Visual/aesthetic concerns
  - Requires human judgment
  - AI can suggest but not auto-create

### Phase IS3: Issue 4-Phase Workflow

"phase_id": "is3"
"status": "planned"
"completion": 0

- [ ] **IS3.1: React Phase**
  - Fully automatic and programmatic
  - Match issue against known solutions
  - Check error message keywords
  - Check context (build system, language, framework)
  - Mark issue as `reacted`
  - If known solution exists: attach solution to issue
  - If no match: pass directly to analyze phase

- [ ] **IS3.2: Analyze Phase**
  - AI analyzes issue
  - Attempts to find solution without code modification
  - AI provides confidence score (0-100)
  - AI describes proposed solution
  - Mark issue as `analyzed`
  - If confidence < 50: suggest iterative fix approach
  - If confidence >= 50: proceed to decide phase

- [ ] **IS3.3: Decide Phase**
  - Automatic if analyze phase confidence >= 80
  - User prompt if confidence < 80
  - User can: approve fix, reject, defer, cancel
  - Mark issue as `decided`
  - If approved: proceed to fix phase
  - If deferred: change priority and re-queue
  - If rejected/cancelled: close issue

- [ ] **IS3.4: Fix Phase**
  - Create dedicated AI session
  - Apply solution (if known from react)
  - Or implement analyzed solution
  - Or use iterative change+test loop
  - Write breadcrumbs throughout
  - Mark issue as `fixing` during work
  - Mark issue as `fixed` when complete
  - Run tests to validate fix

### Phase IS4: Solutions System

"phase_id": "is4"
"status": "planned"
"completion": 0

- [ ] **IS4.1: Solution Schema**
  - Solution ID: auto-generated or descriptive
  - Problem pattern: keywords, regex, error message fragments
  - Applicable contexts: build system, language, framework
  - Solution steps: structured list of actions
  - Confidence applicability: how well pattern matches
  - Success rate: tracked over time

- [ ] **IS4.2: Solution Storage**
  - Store in `docs/solutions/<solution-id>.md`
  - Structured markdown with JSON metadata
  - Version controlled in git
  - Can reference solutions from other repos via hub

- [ ] **IS4.3: Solution Matching**
  - Keyword matching
  - AI similarity scoring
  - Context matching (language, build system)
  - Return multiple matches if applicable
  - Rank by confidence

- [ ] **IS4.4: Solution Management**
  - `maestro solutions add` - AI discussion to extract problem/solution
  - `maestro solutions list` - Show all solutions
  - `maestro solutions show <id>` - Show solution details
  - `maestro solutions remove <id>` - Delete solution
  - `maestro solutions edit <id>` - Edit in $EDITOR

- [ ] **IS4.5: External Solutions**
  - Query solutions from other repos via `$HOME/.maestro/` index
  - Hub integration for shared solutions
  - Remote solution repositories (future)

### Phase IS5: Runtime Issue Collection (Low Priority)

"phase_id": "is5"
"status": "proposed"
"completion": 0

- [ ] **IS5.1: Instrumentation Libraries**
  - C++ support library (RAII-based reporting)
  - Java support library (exception handler)
  - Python support library (logging integration)
  - Support for custom logging frameworks

- [ ] **IS5.2: Collection Endpoints**
  - HTTP endpoint (POST to local server)
  - Unix socket endpoint
  - Log file monitoring (tail -f)
  - Configurable per project

- [ ] **IS5.3: Privacy & Security**
  - Local-only by default
  - Optional sanitization of sensitive data
  - Configurable reporting levels

---

## Track: Work & Session Framework

"track_id": "work-session"
"priority": 3
"status": "planned"
"completion": 0%

This track implements the AI pair programming system with hierarchical session management and breadcrumb tracking.

**Command Hierarchy**:
- `maestro work any` - AI selects and works on best task
- `maestro work any pick` - AI shows top 3 options, user picks
- `maestro work track` - List tracks, user picks (or AI picks if using `any`)
- `maestro work track <id>` - Work on specific track
- `maestro work phase` - List phases, user picks
- `maestro work phase <id>` - Work on specific phase
- `maestro work issue` - List issues, user picks
- `maestro work issue <id>` - Work on specific issue
- `maestro session` - List all sessions
- `maestro session tree` - Show session hierarchy tree
- `maestro session <id>` - Show session details
- `maestro discuss` - General AI discussion (creates session)

### Phase WS1: Session Infrastructure

"phase_id": "ws1"
"status": "planned"
"completion": 0

- [ ] **WS1.1: Session Data Model**
  - Session ID: auto-generated UUID or timestamp-based
  - Session type: work_track, work_phase, work_issue, discussion, analyze, fix
  - Parent session: link to parent if this is a sub-worker
  - Status: running, paused, completed, interrupted, failed
  - Created: timestamp
  - Modified: timestamp
  - Related entity: track_id, phase_id, issue_id, etc.

- [ ] **WS1.2: Session Storage**
  - Store in `docs/sessions/<session-id>/`
  - `session.json` - metadata
  - `breadcrumbs/` - subdirectory for breadcrumbs
  - Nested sessions: `docs/sessions/<parent-id>/<child-id>/`
  - Depth indicated by directory nesting level

- [ ] **WS1.3: Session Lifecycle**
  - Create session on any AI interaction
  - Auto-create child sessions when AI calls sub-workers
  - Handle interruptions (connection lost, errors)
  - Resume interrupted sessions
  - Session completion criteria

- [ ] **WS1.4: Session Pausing (Interactive Mode)**
  - AI can ask questions via JSON response
  - JSON interpreted as user prompt
  - Tool call to blocking executable (maestro proxy)
  - User responds via UI
  - Response passed to new session with parent breadcrumbs
  - Continue execution

### Phase WS2: Breadcrumb System

"phase_id": "ws2"
"status": "planned"
"completion": 0

- [ ] **WS2.1: Breadcrumb Schema**
  - Timestamp: auto-added by maestro (not AI)
  - Prompt: input prompt text
  - Response: AI response (can be JSON)
  - Tools called: list of tool invocations
  - Files modified: list of file paths with diffs
  - Parent session: reference if applicable
  - Depth level: directory depth in session tree
  - Model used: AI model name (sonnet, opus, haiku)
  - Token count: input/output tokens
  - Cost: estimated cost

- [ ] **WS2.2: Breadcrumb Storage**
  - Store in `docs/sessions/<session-id>/breadcrumbs/<depth>/`
  - One file per breadcrumb: `<timestamp>.json`
  - Timestamped by maestro, not AI
  - Full AI dialog can be parsed into multiple breadcrumbs

- [ ] **WS2.3: Breadcrumb Writing**
  - All AI JSON responses are breadcrumbs
  - AI dialog (with tool use) parsed as breadcrumbs
  - Automatic breadcrumb writing (default on)
  - Configurable in `docs/Settings.md` (can disable)
  - Sub-worker breadcrumbs in nested directories

- [ ] **WS2.4: Breadcrumb Reading**
  - Parse session directory tree
  - Reconstruct session timeline
  - Show parent→child relationships
  - Display what was done and why

### Phase WS3: Work Command

"phase_id": "ws3"
"status": "planned"
"completion": 0

- [ ] **WS3.1: Work Selection Algorithm**
  - AI evaluates open tracks/phases/issues
  - Pair-wise comparison or bulk sorting
  - Return JSON with sorted list
  - Consider: priority, dependencies, complexity, user preferences

- [ ] **WS3.2: Work Any**
  - `maestro work any` - AI picks and starts working
  - Auto-create session
  - Write breadcrumbs
  - Report progress
  - Complete or pause with questions

- [ ] **WS3.3: Work Any Pick**
  - `maestro work any pick` - AI shows top 3 options
  - Display: type (track/phase/issue), name, reason
  - User selects from list
  - Proceed with selected work

- [ ] **WS3.4: Work Track/Phase/Issue**
  - List entities if no ID provided
  - AI sorting of list
  - User selection
  - Start work session
  - Link session to entity

- [ ] **WS3.5: Work Integration with Issues**
  - When working on issue: follow 4-phase workflow
  - Create analyze session, decide session, fix session
  - Link sessions in parent-child relationship
  - Timeline shows full workflow

### Phase WS4: Session Visualization

"phase_id": "ws4"
"status": "planned"
"completion": 0

- [ ] **WS4.1: Session List**
  - `maestro session` - list all sessions
  - Show: session ID, type, status, created, related entity
  - Filter by: status, type, date range
  - Sort by: created, modified

- [ ] **WS4.2: Session Tree**
  - `maestro session tree` - show hierarchy
  - Text-based tree (like `tree` command)
  - Show parent→child relationships
  - Indent by depth level
  - Color-code by status (running=green, paused=yellow, failed=red, completed=blue)
  - Emoji indicators for status

- [ ] **WS4.3: Session Details**
  - `maestro session <id>` - show full session
  - Display all breadcrumbs in chronological order
  - Show tools called
  - Show files modified with diffs
  - Show token counts and costs
  - Display sub-sessions

### Phase WS5: Migrate CLI Discussions to Sessions

"phase_id": "ws5"
"status": "planned"
"completion": 0

- [ ] **WS5.1: Update Discussion Commands**
  - `maestro track <id> discuss` - create discussion session
  - `maestro phase <id> discuss` - create discussion session
  - `maestro discuss` - general discussion session
  - All create sessions with breadcrumbs

- [ ] **WS5.2: Backward Compatibility**
  - Maintain existing CLI3 discussion interface
  - Editor mode and terminal mode still work
  - `/done` and `/quit` commands work
  - JSON action processor works
  - But all wrapped in session framework

- [ ] **WS5.3: Session-Aware Actions**
  - JSON actions from discussions create breadcrumbs
  - Link discussion sessions to entities (tracks/phases)
  - Display discussion history via `session tree`

---

## Track: Observability

"track_id": "observability"
"priority": 4
"status": "planned"
"completion": 0%

This track implements visualization and logging of project state, dependencies, and history.

**Command Hierarchy**:
- `maestro hub` - Show repository hub (dependencies, index)
- `maestro hub repos` - List all known repos
- `maestro hub deps` - Show dependency graph
- `maestro hub export` - Export PlantUML diagram
- `maestro log` - Show recent activity
- `maestro log git` - Show git commits
- `maestro log events` - Show all maestro events (sessions, changes)
- `maestro log builds` - Show build history
- `maestro log filter <criteria>` - Filtered log view

### Phase OB1: Hub System

"phase_id": "ob1"
"status": "planned"
"completion": 0

- [ ] **OB1.1: Global Repository Index**
  - `$HOME/.maestro/repos.json` - index of all known repos
  - Auto-updated by all maestro instances
  - Schema: repo path, name, assemblies, packages, last accessed
  - Incremental updates

- [ ] **OB1.2: Hub Commands**
  - `maestro hub` - show current repo info and known repos
  - `maestro hub repos` - list all repos in index
  - `maestro hub deps` - show dependency graph (packages, assemblies)
  - Text-based visualization

- [ ] **OB1.3: Cross-Repo Solutions**
  - Query solutions from other repos
  - Search by problem pattern
  - Display source repo for each solution

- [ ] **OB1.4: Dependency Graph**
  - Build dependency graph from package imports/includes
  - Show internal dependencies (within repo)
  - Show external dependencies (from other repos or system)
  - Detect circular dependencies

- [ ] **OB1.5: Export & Visualization**
  - Export to PlantUML format
  - Export to DOT (Graphviz) format
  - Export to JSON for custom tools
  - TUI integration (future)

### Phase OB2: Log System

"phase_id": "ob2"
"status": "planned"
"completion": 0

- [ ] **OB2.1: Event Logging**
  - Log all maestro actions to `docs/log.md`
  - Event types: session_start, session_end, build, issue_created, issue_fixed, etc.
  - Timestamp, event type, details
  - Append-only log

- [ ] **OB2.2: Log Views**
  - `maestro log` - recent activity (last 20 events)
  - `maestro log git` - git commit history
  - `maestro log events` - all maestro events
  - `maestro log builds` - build history (success/failure)
  - `maestro log sessions` - all sessions

- [ ] **OB2.3: Log Filtering**
  - Filter by date range: `--since`, `--until`
  - Filter by event type: `--type build,issue`
  - Filter by track/phase: `--track umk`
  - Filter by user: `--user <name>`
  - Filter by AI model: `--model sonnet`

- [ ] **OB2.4: Build History**
  - Track successful builds
  - Track failed builds with error counts
  - Track build duration
  - Show build trends over time

### Phase OB3: Global Repo Index Management

"phase_id": "ob3"
"status": "planned"
"completion": 0

- [ ] **OB3.1: Index Updates**
  - Auto-update index on `maestro init`
  - Auto-update index on `maestro repo resolve`
  - Incremental updates (don't rewrite entire file)
  - Locking for concurrent access

- [ ] **OB3.2: Index Queries**
  - Search repos by name
  - Search repos by assembly type (U++, CMake, etc.)
  - Search repos by language (C++, Java, Python)
  - Search repos by last modified date

- [ ] **OB3.3: Remote Index (Future)**
  - Share index across machines
  - Remote repository catalog
  - Built-in index of well-known repos
  - Index synchronization

---

## Track: Code Transformation

"track_id": "code-transformation"
"priority": 5
"status": "planned"
"completion": 0%

This track extends the completed TU/AST system (TU1-TU7) with issue-fixing and conversion capabilities.

**Command Hierarchy**:
- `maestro convert` - Show conversion options
- `maestro convert <source-lang> <target-lang> <path>` - Convert code
- `maestro tu analyze <binary>` - Analyze built executable for TU/AST
- `maestro tu print-ast <file>` - Print AST (already implemented)

### Phase CT1: TU/AST for Issue Fixing

"phase_id": "ct1"
"status": "planned"
"completion": 0

- [ ] **CT1.1: Error Message Symbol Extraction**
  - Parse compiler error messages
  - Extract class names, function names, variable names, field names
  - Match symbols against previous successful TU/AST
  - Find symbol definitions and declarations

- [ ] **CT1.2: AST Hints for AI**
  - When fixing build issue: provide AST context
  - Show symbol definition from AST
  - Show usage examples from AST
  - Show type information from AST
  - Include in AI prompt for better fix suggestions

- [ ] **CT1.3: Convention Checking via AST**
  - Check naming conventions against AST
  - Detect convention violations automatically
  - Create convention issues
  - Suggest fixes based on AST analysis

### Phase CT2: Conversion Pipeline

"phase_id": "ct2"
"status": "planned"
"completion": 0

- [ ] **CT2.1: Conversion Framework**
  - Leverage TU1-TU7 infrastructure
  - Parser → AST → Transform → Target AST → Code Gen
  - Language-agnostic intermediate representation
  - Preserve semantics where possible

- [ ] **CT2.2: Build System Conversion**
  - Convert Makefile → CMakeLists.txt
  - Convert Autotools → CMake
  - Convert Maven → Gradle
  - Framework for custom conversions

- [ ] **CT2.3: Framework Conversion**
  - Qt → wxWidgets (experimental)
  - Custom framework mapping rules
  - AI-assisted conversion decisions

- [ ] **CT2.4: IDE Project Export** (from UMK Phase 11)
  - Export package groups to Visual Studio filters (.vcxproj.filters)
  - Export package groups to CMake source_group()
  - Export package groups to IntelliJ modules
  - Preserve internal package group structure in IDE projects

### Phase CT3: Multi-Language Convert (Experimental)

"phase_id": "ct3"
"status": "proposed"
"completion": 0

- [ ] **CT3.1: Language Conversion Experiments**
  - C++ → Java (basic)
  - C++ → Python (basic)
  - Java → Python
  - Real-world case studies

- [ ] **CT3.2: Conversion Quality**
  - Validate converted code compiles
  - Validate converted code has same behavior
  - Manual review and refinement
  - Document conversion limitations

- [ ] **CT3.3: Conversion Templates**
  - Common idiom mappings (C++ RAII → Python context manager)
  - Type system mappings (C++ templates → Java generics)
  - Standard library mappings (STL → Java Collections)

---

## Track: Cleanup & Migration

"track_id": "cleanup-migration"
"priority": 6
"status": "planned"
"completion": 0%

This track removes deprecated commands and migrates to new systems.

### Phase CM1: Remove Deprecated Commands

"phase_id": "cm1"
"status": "planned"
"completion": 0

**Deprecated Commands**:
- `maestro plan` → Use `maestro phase`
- `maestro task` → Use `maestro track` and `maestro phase`
- `maestro root` → Use initial track
- `maestro context` → Use `maestro work` (auto-selects context)
- `maestro refine-root` → Removed (not needed)
- `maestro build` → Use `maestro make`

- [ ] **CM1.1: Mark Commands as Deprecated**
  - Add deprecation warnings to command handlers
  - Show migration path in warning message
  - Update help text with deprecation notice

- [ ] **CM1.2: Create Migration Guide**
  - Document in `docs/MIGRATION.md`
  - Show before/after command examples
  - Explain rationale for changes

- [ ] **CM1.3: Remove Commands**
  - Remove command implementations
  - Remove from argparse
  - Remove from help system
  - Update all documentation

### Phase CM2: Rename Settings File

"phase_id": "cm2"
"status": "planned"
"completion": 0

- [ ] **CM2.1: Rename Configuration**
  - `docs/config.md` → `docs/Settings.md`
  - Update CLI4 implementation
  - Auto-migrate on `maestro init` or first run
  - Update settings parser

- [ ] **CM2.2: Update Documentation**
  - Update all references in docs
  - Update CLI help text
  - Update phase files (cli4.md)

### Phase CM3: Update Help System

"phase_id": "cm3"
"status": "planned"
"completion": 0

- [ ] **CM3.1: Reorganize --help Output**
  - Reflect new command hierarchy order:
    1. init
    2. repo (resolve, refresh, hier, conventions, rules)
    3. track, phase
    4. make
    5. run
    6. discuss
    7. issues (all categories)
    8. solutions
    9. work
    10. session
    11. hub, log
    12. convert, tu

- [ ] **CM3.2: Improve Help Text**
  - Add usage examples to help
  - Add "See also" references
  - Group related commands visually
  - Color-code help output

---

## ✅ COMPLETED Track: Track/Phase/Task CLI and AI Discussion System

"track_id": "cli-tpt"
"priority": 7
"status": "done"
"completion": 100%

This track implements the new Track/Phase/Task command-line interface with integrated AI discussion capabilities, and migrates all data storage from `.maestro/` JSON files to `docs/` markdown files.

**Track Completed**: 2025-12-19
**All phases (CLI1-CLI5) completed and documented in docs/done.md**

**Migration Notes**:
- CLI3 (AI Discussion System) will be deprecated and replaced by Session Framework (WS5)
- CLI4 (Settings) needs migration from `docs/config.md` to `docs/Settings.md` (CM2)
- CLI1, CLI2, CLI5 remain as-is and are foundational

**Core Concepts:**
- **TODO vs DONE**: Past and future separation throughout the entire architecture
- **Track/Phase/Task**: New hierarchy replacing the old Roadmap/Plan/Task
- **AI Discussion**: Unified discussion interface for tracks, phases, and tasks
- **Markdown Storage**: All data in human-readable, machine-parsable markdown

### Phase CLI1: Markdown Data Backend

"phase_id": "cli-tpt-1"
"status": "done"
"completion": 100

- [x] [Phase CLI1: Markdown Data Backend](phases/cli1.md) ✅ **[Done]**
  - Parser module for markdown data format
  - Writer module for markdown data format
  - Migration from JSON to markdown
  - Data validation and error recovery

### Phase CLI2: Track/Phase/Task Commands

"phase_id": "cli-tpt-2"
"status": "done"
"completion": 100

- [x] [Phase CLI2: Track/Phase/Task Commands](phases/cli2.md) ✅ **[Done]**
  - `maestro track {help,list,add,remove,<id>}` commands
  - `maestro phase {help,list,add,remove,<id>}` commands
  - `maestro task {help,list,add,remove,<id>}` commands
  - `maestro track <id> phase` navigation
  - `maestro {track,phase,task} <id> {show,edit}` subcommands

### Phase CLI3: AI Discussion System

"phase_id": "cli-tpt-3"
"status": "done"
"completion": 100
"notes": "⚠️ Will be migrated to Session Framework in WS5"

- [x] [Phase CLI3: AI Discussion System](phases/cli3.md) ⚠️ **[Done - Needs Migration]**
  - Unified discussion module for all AI interactions
  - `maestro track discuss` - general track planning
  - `maestro phase <id> discuss` - phase-specific discussion
  - `maestro task <id> discuss` - task-specific discussion
  - Editor mode ($EDITOR) with # comment syntax
  - Terminal stream mode (Enter to send, Ctrl+J for newline)
  - `/done` command to finish and generate JSON actions
  - `/quit` command to cancel
  - JSON action processor for track/phase/task operations
  - Settings management: `maestro settings` for defaults

### Phase CLI4: Settings and Configuration

"phase_id": "cli-tpt-4"
"status": "done"
"completion": 100
"notes": "⚠️ Needs migration from config.md to Settings.md in CM2"

- [x] [Phase CLI4: Settings and Configuration](phases/cli4.md) ⚠️ **[Done - Needs Migration]**
  - Move all config from `~/.maestro/` to `docs/config.md`
  - `maestro settings` command
  - User preferences (editor mode, AI context, etc.)
  - Project-level settings in docs/config.md

### Phase CLI5: TUI Track/Phase/Task Conversion

"phase_id": "cli-tpt-5"
"status": "done"
"completion": 100

- [x] [Phase CLI5: TUI Conversion](phases/cli5.md) ✅ **[Done]**
  - Convert TUI to use Track/Phase/Task terminology
  - Integrate with markdown data backend
  - Update status badges and visual indicators
  - Feature parity with CLI commands
  - Deprecate or update textual-mc

---

## Primary Track: UMK Integration (Universal Build System)

"track_id": "umk"
"priority": 8
"status": "in_progress"

This track implements all phases from `docs/umk.md`, creating a universal build orchestration system.

**Integration with New System**:
- UMK builder system will be used by `maestro make` command (BR1)
- Builder errors will create issues automatically (BR1.3)
- Build configurations will be used by `maestro run` command (BR3)
- Phase 11 (Internal Package Groups) integrated into:
  - RF2.1: Group detection and parsing
  - RF2.2: Group visualization CLI/TUI
  - BR1.1: Group-specific builds
  - CT2.4: IDE project export

- [ ] [Phase 1: Core Builder Abstraction](phases/phase1.md) ✅ **[Design Complete]** 📋 **[Implementation Planned]**
- [ ] [Phase 2: U++ Builder Implementation](phases/phase2.md) 📋 **[Planned]**
- [ ] [Phase 3: CMake Builder](phases/phase3.md) 📋 **[Planned]**
- [ ] [Phase 4: Autotools Builder](phases/phase4.md) 📋 **[Planned]**
- [ ] [Phase 5: MSBuild / Visual Studio Builder](phases/phase5.md) 📋 **[Planned]**
- [ ] [Phase 5.5: Maven Builder](phases/phase5_5.md) 📋 **[Planned]**
- [ ] [Phase 6: Universal Build Configuration](phases/phase6.md) 📋 **[Planned]**
- [ ] [Phase 7: CLI Integration](phases/phase7.md) 📋 **[Planned]**
- [ ] [Phase 8: Advanced Features](phases/phase8.md) 📋 **[Planned]**
- [ ] [Phase 9: TUI Integration](phases/phase9.md) 📋 **[Planned]**
- [ ] [Phase 10: Universal Hub System (MaestroHub)](phases/phase10.md) 📋 **[Planned]**
- [ ] [Phase 11: Internal Package Groups](phases/phase11.md) 📋 **[Planned]**
- [ ] [Phase 12: Retroactive Fixes and Missing Components](phases/phase12.md) 🚧 **[CURRENT - Critical]**

---

## Track: Test Meaningfulness & Reliability

"track_id": "test-meaningfulness"
"priority": 9
"status": "planned"

This track focuses on evaluating and improving the meaningfulness and reliability of the test suite so failures reflect real regressions, not environment noise.

### Phase TM1: Test Meaningfulness Audit

"phase_id": "test-meaningfulness-1"
"status": "planned"
"completion": 0

- [ ] [Phase TM1: Test Meaningfulness Audit](phases/tm1.md) 📋 **[Planned]**
  - Categorize failing tests by value and stability
  - Decide which tests to fix, update, or retire

---

## ✅ COMPLETED Track: TU/AST System

"track_id": "tu-ast"
"priority": 10
"status": "done"
"completion": 100%

This track implements Translation Unit (TU) and Abstract Syntax Tree (AST) generation for advanced code analysis, auto-completion, and code transformation.

**Integration with New System**:
- TU/AST system will be extended for issue fixing (CT1)
- Conversion pipeline will leverage TU1-TU7 (CT2)
- AST analysis will detect convention violations (CT1.3)

- [x] [Phase TU1: Core AST Infrastructure](phases/tu1.md) ✅ **[Done - 2025-12-19]**
- [x] [Phase TU2: Incremental TU Builder with File Hashing](phases/tu2.md) ✅ **[Done - 2025-12-19]**
- [x] [Phase TU3: Symbol Resolution and Indexing](phases/tu3.md) ✅ **[Done - 2025-12-19]**
- [x] [Phase TU4: Auto-Completion Engine](phases/tu4.md) ✅ **[Done - 2025-12-19]**
- [x] [Phase TU5: Integration with Build System and CLI](phases/tu5.md) ✅ **[Done - 2025-12-19]**
- [x] [Phase TU6: Code Transformation and Convention Enforcement](phases/tu6.md) ✅ **[Done - 2025-12-19]**
- [x] [Phase TU7: Multi-Language AST Testing](phases/tu7.md) ✅ **[Done - 2025-12-19]**

---

## Extended Track: Additional Build Systems

"track_id": "extended"
"priority": 11
"status": "planned"
"completion": 0%

This track extends repository scanning and build support to additional ecosystems.

**Integration with New System**:
- Extended build systems will integrate with `maestro make` (BR1)
- Package scanning will be used by `repo resolve` (RF1)
- Assembly detection (completed in AS1) integrated into `repo hier` (RF2)

- [ ] [Phase E1: Python Project Support](phases/e1.md) 📋 **[Planned]**
- [ ] [Phase E2: Node.js / npm Project Support](phases/e2.md) 📋 **[Planned]**
- [ ] [Phase E3: Go Project Support](phases/e3.md) 📋 **[Planned]**
- [ ] [Phase E4: Pedigree pup Package System Support](phases/e4.md) 📋 **[Planned]**
- [ ] [Phase E5: Additional Build Systems (Future)](phases/e5.md) 💡 **[Proposed]**

---

## Advanced Track: External Dependencies and Portage Integration

"track_id": "advanced"
"priority": 12
"status": "proposed"
"completion": 0%

This track handles external dependencies, build scripts, and Gentoo Portage integration.

- [ ] [Phase A1: Git Submodule and Build Script Handling](phases/a1.md) 💡 **[Proposed]**
- [ ] [Phase A2: Gentoo Portage Integration - Design](phases/a2.md) 💡 **[Proposed]**
- [ ] [Phase A3: Portage Integration - Implementation](phases/a3.md) 💡 **[Proposed]**
- [ ] [Phase A4: Host System Package Recognition](phases/a4.md) 💡 **[Proposed]**
- [ ] [Phase A5: Portage Superset Integration](phases/a5.md) 💡 **[Proposed]**
- [ ] [Phase A6: External Dependency Workflow](phases/a6.md) 💡 **[Proposed]**

---

## Integration and Testing

- [ ] [Phase IT1: Integration Testing](phases/it1.md)
- [ ] [Phase IT2: Notes and Considerations](phases/it2.md)
- [ ] [Phase IT3: Next Steps](phases/it3.md)

---

**Document Status**: Major restructuring complete. New tracks and phases defined for next-generation AI-powered development workflow.
**Last Review**: 2025-12-19
