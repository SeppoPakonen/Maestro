"""
Dataclasses and type definitions for Maestro.
"""
import time
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

# Dataclasses for builder configuration
@dataclass
class StepConfig:
    """Configuration for a single pipeline step."""
    cmd: List[str]
    optional: bool = False


@dataclass
class ValgrindConfig:
    """Configuration for valgrind analysis."""
    enabled: bool = False
    cmd: List[str] = field(default_factory=list)


@dataclass
class PipelineConfig:
    """Configuration for the entire pipeline."""
    steps: List[str] = field(default_factory=list)


@dataclass
class BuilderConfig:
    """Main builder configuration."""
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)
    step: Dict[str, StepConfig] = field(default_factory=dict)
    valgrind: ValgrindConfig = field(default_factory=ValgrindConfig)


@dataclass
class StepResult:
    """Result data for a single pipeline step."""
    step_name: str
    exit_code: int
    stdout: str
    stderr: str
    duration: float
    success: bool


@dataclass
class PipelineRunResult:
    """Result data for the entire pipeline run."""
    timestamp: float
    step_results: List[StepResult]
    success: bool


@dataclass
class Diagnostic:
    """Structured diagnostic with stable fingerprint."""
    tool: str                    # e.g. "gcc", "clang", "msvc", "valgrind", "lint"
    severity: str               # "error" | "warning" | "note"
    file: Optional[str]         # File path where issue occurred
    line: Optional[int]         # Line number where issue occurred
    message: str                # Normalized message
    raw: str                    # Original diagnostic line(s)
    signature: str              # Computed fingerprint
    tags: List[str]             # e.g. ["upp", "moveable", "template", "vector"]
    known_issues: List['KnownIssue'] = field(default_factory=list)  # Matched known issues


# Dataclasses for reactive fix rules
@dataclass
class MatchCondition:
    """Condition for matching diagnostics to rules."""
    contains: Optional[str] = None
    regex: Optional[str] = None

@dataclass
class RuleMatch:
    """Configuration for matching diagnostics."""
    any: List[MatchCondition] = field(default_factory=list)  # At least one condition must match
    not_conditions: List[MatchCondition] = field(default_factory=list, repr=False)  # None of these conditions should match

@dataclass
class StructureFixAction:
    """Structure fix action configuration."""
    type: str  # Always "structure_fix"
    apply_rules: List[str]  # List of structure rule names to apply
    limit: Optional[int] = None  # Optional limit on number of operations


@dataclass
class RuleAction:
    """Action to take when a rule matches."""
    type: str  # "hint" | "prompt_patch" | "structure_fix"
    text: Optional[str] = None
    model_preference: List[str] = field(default_factory=list)
    prompt_template: Optional[str] = None
    # For structure_fix type, we'll have additional fields in the JSON
    apply_rules: List[str] = field(default_factory=list)  # For "structure_fix" type
    limit: Optional[int] = None  # For "structure_fix" type

@dataclass
class RuleVerify:
    """Verification configuration for the rule."""
    expect_signature_gone: bool = True

@dataclass
class Rule:
    """A single rule in a rulebook."""
    id: str
    enabled: bool
    priority: int
    match: RuleMatch
    confidence: float
    explanation: str
    actions: List[RuleAction]
    verify: RuleVerify

@dataclass
class Rulebook:
    """A collection of fix rules."""
    version: int
    name: str
    description: str
    rules: List[Rule]

@dataclass
class ConversionStage:
    """Represents a single stage in the conversion pipeline."""
    name: str
    status: str  # "pending", "running", "completed", "failed", "skipped"
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = field(default_factory=dict)

@dataclass
class ConversionPipeline:
    """Represents the conversion pipeline state."""
    id: str
    name: str
    source: str
    target: str
    created_at: str
    updated_at: str
    status: str  # "new", "running", "completed", "failed", "paused"
    stages: List[ConversionStage] = field(default_factory=list)
    active_stage: Optional[str] = None
    logs_dir: Optional[str] = None
    inputs_dir: Optional[str] = None
    outputs_dir: Optional[str] = None
    source_repo: Optional[Dict[str, Any]] = None  # Enhanced source repo details
    target_repo: Optional[Dict[str, Any]] = None  # Enhanced target repo details
    conversion_intent: Optional[str] = None       # Conversion intent taxonomy


@dataclass
class BatchJobSpec:
    """Represents a single job in a batch spec."""
    name: str
    source: str
    target: str
    intent: str
    playbook: Optional[str] = None
    baseline: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    rehearse: Optional[bool] = None
    auto_replan: Optional[bool] = None
    arbitrate: Optional[bool] = None
    max_candidates: Optional[int] = None
    judge_engine: Optional[str] = None
    checkpoint_mode: Optional[str] = None
    semantic_strict: Optional[str] = None


@dataclass
class BatchDefaults:
    """Default values for batch jobs."""
    rehearse: bool = True
    auto_replan: bool = False
    arbitrate: bool = True
    max_candidates: int = 2
    judge_engine: str = "codex"
    checkpoint_mode: str = "manual"
    semantic_strict: bool = True


@dataclass
class BatchSpec:
    """Represents a batch specification for multiple conversion jobs."""
    batch_id: str
    defaults: BatchDefaults
    jobs: List[BatchJobSpec]
    description: Optional[str] = None

@dataclass
class MatchedRule:
    """A rule that has been matched to a diagnostic."""
    rule: Rule
    diagnostic: Diagnostic
    confidence: float


@dataclass
class FixIteration:
    """Data for a single fix iteration in the fix run."""
    iteration: int
    selected_target_signatures: List[str]
    matched_rule_ids: List[str]
    model_used: str
    patch_kept: bool
    patch_reason: Optional[str] = None
    verification_result: bool = False
    new_signatures_introduced: List[str] = field(default_factory=list)
    errors_before: int = 0
    errors_after: int = 0
    timestamp: float = field(default_factory=time.time)


@dataclass
class FixRun:
    """Data for a complete fix run with all iterations."""
    fix_run_id: str
    session_path: str
    start_time: float
    iterations: List[FixIteration] = field(default_factory=list)
    end_time: Optional[float] = None
    completed: bool = False

# Dataclass for build target configuration
@dataclass
class BuildTarget:
    """Configuration for a build target."""
    target_id: str
    name: str
    created_at: str
    categories: List[str] = field(default_factory=list)
    description: str = ""
    why: str = ""  # Planner rationale / intent
    pipeline: Dict[str, Any] = field(default_factory=dict)
    patterns: Dict[str, Any] = field(default_factory=dict)
    environment: Dict[str, Any] = field(default_factory=dict)


# Dataclasses for U++ package discovery
@dataclass
class UppPackage:
    """Represents a U++ package with its files and metadata."""
    name: str
    dir_path: str
    upp_path: str
    main_header_path: Optional[str]
    source_files: List[str] = field(default_factory=list)
    header_files: List[str] = field(default_factory=list)
    is_dependency_library: bool = False


@dataclass
class UppFile:
    """Represents a file entry within a UppProject."""
    path: str = ""
    separator: bool = False
    readonly: bool = False
    pch: bool = False
    nopch: bool = False
    noblitz: bool = False
    charset: str = ""
    tabsize: int = 0
    font: int = 0
    highlight: str = ""
    spellcheck_comments: str = ""
    options: List[str] = field(default_factory=list)
    depends: List[str] = field(default_factory=list)


@dataclass
class UppConfig:
    """Represents a mainconfig entry."""
    name: str = ""
    param: str = ""


@dataclass
class UppProject:
    """Represents a U++ project configuration from an .upp file."""
    uses: List[str] = field(default_factory=list)
    mainconfig: List[UppConfig] = field(default_factory=list)  # List of config name/value pairs
    files: List[UppFile] = field(default_factory=list)  # List of file entries
    description: str = ""
    description_ink: Optional[tuple] = None  # RGB tuple for color (r, g, b)
    description_bold: bool = False
    description_italic: bool = False
    options: List[str] = field(default_factory=list)
    flags: List[str] = field(default_factory=list)
    target: List[str] = field(default_factory=list)
    library: List[str] = field(default_factory=list)
    static_library: List[str] = field(default_factory=list)
    link: List[str] = field(default_factory=list)
    include: List[str] = field(default_factory=list)
    pkg_config: List[str] = field(default_factory=list)
    accepts: List[str] = field(default_factory=list)
    charset: str = ""
    tabsize: Optional[int] = None
    noblitz: bool = False
    nowarnings: bool = False
    spellcheck_comments: str = ""
    custom_steps: List[Dict] = field(default_factory=list)
    unknown_blocks: List[str] = field(default_factory=list)  # Preserve unknown content
    file_separators: List[str] = field(default_factory=list)  # Preserve file separators for compatibility
    sections: List[Dict] = field(default_factory=list)  # List of sections with their content - for compatibility
    raw_content: str = ""  # Preserve original content for reference


@dataclass
class UppRepoIndex:
    """Index of U++ assemblies and packages in a repository."""
    assemblies: List[str]
    packages: List[UppPackage]


@dataclass
class PackageInfo:
    """Information about a detected package (U++, CMake, Make, etc.)."""
    name: str
    dir: str
    upp_path: str
    files: List[str] = field(default_factory=list)
    upp: Optional[Dict[str, Any]] = None  # Parsed .upp metadata
    build_system: str = 'upp'  # 'upp', 'cmake', 'make', 'autoconf', 'gradle', 'maven'
    dependencies: List[str] = field(default_factory=list)  # Project dependencies
    groups: List['FileGroup'] = field(default_factory=list)  # Internal package groups
    ungrouped_files: List[str] = field(default_factory=list)  # Files not in any group


@dataclass
class AssemblyInfo:
    """Information about a detected assembly."""
    name: str
    root_path: str
    package_folders: List[str] = field(default_factory=list)
    evidence_refs: List[str] = field(default_factory=list)  # References like "found in xyz.var"
    # Additional fields for new assembly features:
    assembly_type: str = 'upp'  # 'upp', 'python', 'java', 'gradle', 'maven', 'misc', 'multi'
    packages: List[str] = field(default_factory=list)  # List of package names contained in this assembly
    package_dirs: List[str] = field(default_factory=list)  # List of package directory paths
    build_systems: List[str] = field(default_factory=list)  # List of build systems used
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UnknownPath:
    """Information about an unknown path in the repository."""
    path: str
    type: str  # 'file' or 'dir'
    guessed_kind: str  # 'docs', 'tooling', 'third_party', 'scripts', 'assets', 'config', 'unknown'


@dataclass
class InternalPackage:
    """Maestro internal package grouping for non-U++ paths."""
    name: str
    root_path: str
    guessed_type: str  # 'docs', 'tooling', 'scripts', 'assets', 'third_party', 'misc'
    members: List[str] = field(default_factory=list)  # Relative paths of members


@dataclass
class RepoScanResult:
    """Result of scanning a U++ repository for packages, assemblies, and unknown paths."""
    assemblies_detected: List[AssemblyInfo] = field(default_factory=list)
    packages_detected: List[PackageInfo] = field(default_factory=list)
    unknown_paths: List[UnknownPath] = field(default_factory=list)
    user_assemblies: List[Dict[str, Any]] = field(default_factory=list)  # From ~/.config/u++/ide/*.var
    internal_packages: List[InternalPackage] = field(default_factory=list)  # Inferred from unknown paths


# Dataclasses for structure fix operations
@dataclass
class FixOperation:
    """Base class for a fix operation."""
    op: str
    reason: str


@dataclass
class RenameOperation(FixOperation):
    """Rename a file or directory."""
    op: str
    reason: str
    from_path: str = ""
    to_path: str = ""


@dataclass
class WriteFileOperation(FixOperation):
    """Write content to a file."""
    op: str
    reason: str
    path: str = ""
    content: str = ""


@dataclass
class EditFileOperation(FixOperation):
    """Edit a file using a patch."""
    op: str
    reason: str
    path: str = ""
    patch: str = ""


@dataclass
class UpdateUppOperation(FixOperation):
    """Update a .upp file."""
    op: str
    reason: str
    path: str = ""
    changes: Dict = field(default_factory=dict)


@dataclass
class FixPlan:
    """A plan containing atomic operations to fix project structure."""
    version: int = 1
    repo_root: str = ""
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    operations: List[FixOperation] = field(default_factory=list)


@dataclass
class StructureRule:
    """A rule for project structure fixes."""
    id: str
    enabled: bool = True
    description: str = ""
    applies_to: str = ""  # "all", "package", "file", etc.

# ANSI color codes for styling
class Colors:
    # Text colors
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'

    # Bright colors
    BRIGHT_RED = '\033[91m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_BLUE = '\033[94m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'

    # Formatting
    BOLD = '\033[1m'
    DIM = '\033[2m'
    ITALIC = '\033[3m'

    # Reset
    RESET = '\033[0m'

# Legacy hard-coded subtask titles for safety checking
LEGACY_TITLES = {
    "Analysis and Research",
    "Implementation",
    "Testing and Integration",
}
