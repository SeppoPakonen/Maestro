"""
Runbook command for Maestro CLI - runbook-first bootstrap before workflow.

This command provides tools for managing runbook entries as first-class project assets
stored in repo truth (JSON). Runbooks are a lower-friction, narrative-first modeling layer
that can later feed Workflow graphs.
"""
import argparse
import json
import os
import re
import hashlib
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol
from dataclasses import dataclass

from maestro.config.paths import get_docs_root


@dataclass
class RunbookEvidence:
    """Dataclass to hold repo evidence for runbook generation."""
    repo_root: str
    commands_docs: List[Dict[str, str]]  # List of {filename, title, summary}
    help_text: Optional[str] = None
    help_bin_path: Optional[str] = None
    warnings: List[str] = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


def extract_doc_title_and_summary(content: str) -> tuple[str, str]:
    """Extract title and summary from markdown content."""
    lines = content.split('\n')
    title = ""
    summary = ""

    # Look for first heading as title
    for line in lines:
        if line.strip().startswith('#'):
            title = line.strip().lstrip('#').strip()
            break

    # Look for first paragraph after title as summary
    in_title_section = True
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('#'):
            continue
        if stripped and not stripped.startswith('#'):
            summary = stripped
            break

    return title or "Untitled", summary


def collect_repo_evidence(commands_dir: Optional[str] = None, help_bin: Optional[str] = None) -> RunbookEvidence:
    """Collect repo evidence for runbook generation."""
    repo_root = Path.cwd().resolve()

    # Find commands directory
    if commands_dir is None:
        possible_paths = [
            repo_root / "docs" / "commands",
            repo_root / "docs" / "maestro" / "commands",
            repo_root / "documentation" / "commands"
        ]
        commands_path = None
        for path in possible_paths:
            if path.exists():
                commands_path = path
                break
    else:
        commands_path = Path(commands_dir)

    commands_docs = []
    warnings = []

    if commands_path and commands_path.exists():
        for md_file in commands_path.glob("*.md"):
            try:
                content = md_file.read_text(encoding='utf-8')
                title, summary = extract_doc_title_and_summary(content)
                commands_docs.append({
                    'filename': md_file.name,
                    'title': title,
                    'summary': summary
                })
            except Exception as e:
                warnings.append(f"Could not read {md_file}: {str(e)}")
    else:
        if commands_dir:
            warnings.append(f"Commands directory not found: {commands_dir}")
        else:
            warnings.append("No commands documentation directory found")

    # Find help binary
    help_text = None
    help_bin_path = None

    if help_bin:
        bin_path = Path(help_bin)
        if bin_path.exists():
            try:
                result = subprocess.run([str(bin_path), "--help"],
                                      capture_output=True, text=True,
                                      timeout=2, cwd=repo_root)
                if result.returncode == 0:
                    help_text = result.stdout
                    help_bin_path = str(bin_path)
                else:
                    warnings.append(f"Binary --help command failed: {result.stderr}")
            except subprocess.TimeoutExpired:
                warnings.append(f"Binary --help command timed out after 2 seconds")
            except Exception as e:
                warnings.append(f"Error running binary --help: {str(e)}")
        else:
            warnings.append(f"Help binary not found: {help_bin}")
    else:
        # Look for common binary paths
        possible_bins = [
            repo_root / "build_maestro" / "bss",
            repo_root / "build" / "bss",
            repo_root / "bin" / "bss",
            repo_root / "dist" / "bss",
        ]

        for bin_path in possible_bins:
            if bin_path.exists():
                try:
                    result = subprocess.run([str(bin_path), "--help"],
                                          capture_output=True, text=True,
                                          timeout=2, cwd=repo_root)
                    if result.returncode == 0:
                        help_text = result.stdout
                        help_bin_path = str(bin_path)
                        break
                    else:
                        warnings.append(f"Binary --help command failed for {bin_path}: {result.stderr}")
                except subprocess.TimeoutExpired:
                    warnings.append(f"Binary --help command timed out after 2 seconds for {bin_path}")
                except Exception as e:
                    warnings.append(f"Error running binary --help for {bin_path}: {str(e)}")

    return RunbookEvidence(
        repo_root=str(repo_root),
        commands_docs=commands_docs,
        help_text=help_text,
        help_bin_path=help_bin_path,
        warnings=warnings
    )


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    # Convert to lowercase and replace spaces with hyphens
    text = text.lower().replace(' ', '-')
    # Remove special characters except hyphens
    text = re.sub(r'[^a-z0-9\-]', '', text)
    # Remove multiple consecutive hyphens
    text = re.sub(r'-+', '-', text)
    # Remove leading/trailing hyphens
    text = text.strip('-')
    return text


def generate_runbook_id(title: str) -> str:
    """Generate a deterministic runbook ID from title."""
    slug = slugify(title)
    # Create a hash of the normalized title
    title_hash = hashlib.sha256(title.encode('utf-8')).hexdigest()[:8]
    return f"rb-{slug}-{title_hash}"


class RunbookGenerator(Protocol):
    """Interface for runbook generation."""

    def generate(self, evidence: RunbookEvidence, request_text: str) -> Dict[str, Any]:
        """Generate a runbook from evidence and request text."""
        ...


class EvidenceOnlyGenerator:
    """Generator that creates runbooks based only on evidence, without AI."""

    def generate(self, evidence: RunbookEvidence, request_text: str) -> Dict[str, Any]:
        """Generate a runbook based on evidence only."""
        # Generate a title from the request text
        title = request_text[:100] if request_text else "Evidence-based runbook"

        # Generate a deterministic ID
        runbook_id = generate_runbook_id(title)

        # Create the runbook structure
        runbook = {
            'id': runbook_id,
            'title': title,
            'goal': f"Implement commands based on evidence from {evidence.repo_root}",
            'prerequisites': [],
            'steps': [],
            'artifacts': [],
            'invariants': [],
            'tags': ['generated', 'evidence-based'],
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'repo_evidence': {
                'repo_root': evidence.repo_root,
                'commands_docs_count': len(evidence.commands_docs),
                'help_available': evidence.help_text is not None,
                'help_bin_path': evidence.help_bin_path,
                'warnings_count': len(evidence.warnings)
            }
        }

        # Add steps based on evidence
        steps = []

        # Step 1: Verify CLI help is available
        if evidence.help_text:
            steps.append({
                'n': len(steps) + 1,
                'actor': 'dev',
                'action': f'Verify CLI help is available from {evidence.help_bin_path}',
                'expected': 'Help text displays successfully showing available commands'
            })
        else:
            steps.append({
                'n': len(steps) + 1,
                'actor': 'dev',
                'action': 'Verify CLI help is available',
                'expected': 'Help text should be available once the binary is built'
            })

        # Steps for each command documentation file
        for i, doc in enumerate(evidence.commands_docs):
            steps.append({
                'n': len(steps) + 1,
                'actor': 'dev',
                'action': f'Review docs/commands/{doc["filename"]} and create a minimal script exercising {doc["title"]}',
                'expected': f'Semantics of {doc["title"]} captured; add/adjust a test script'
            })

        # Add a final step suggesting next actions
        if evidence.help_bin_path:
            steps.append({
                'n': len(steps) + 1,
                'actor': 'dev',
                'action': f'Run {evidence.help_bin_path} with minimal test script',
                'expected': 'Commands execute as expected; manual verification until build exists'
            })
        else:
            steps.append({
                'n': len(steps) + 1,
                'actor': 'dev',
                'action': 'Build the binary and test with sample commands',
                'expected': 'Binary builds successfully and responds to commands'
            })

        runbook['steps'] = steps

        # Add warnings as prerequisites if any exist
        if evidence.warnings:
            runbook['prerequisites'] = [f'Warning: {warning}' for warning in evidence.warnings]

        return runbook


import sys

class AIRunbookGenerator:
    """Generator that creates runbooks using AI based on evidence and request text."""

    def __init__(self, engine, verbose: bool = False, actionable: bool = False):
        self.engine = engine
        self.verbose = verbose
        self.actionable = actionable
        # Store the last prompt and response for debugging purposes
        self.last_prompt = None
        self.last_response = None

    def generate(self, evidence: RunbookEvidence, request_text: str) -> Dict[str, Any]:
        """Generate a runbook using AI based on evidence and request text."""
        # Create a prompt for the AI that includes both the request and evidence
        prompt = self._create_runbook_generation_prompt(evidence, request_text, actionable=self.actionable)

        # Store the prompt for potential very verbose output
        self.last_prompt = prompt

        if self.verbose:
            print(f"Sending prompt to AI engine (length: {len(prompt)} chars)...")

        # Generate the response using the AI engine
        response = self.engine.generate(prompt)

        # Store the response for potential very verbose output
        self.last_response = response

        if self.verbose:
            print(f"AI response received (length: {len(response)} chars)")

        # Try to parse the response as JSON
        try:
            # First, try to extract JSON from the response if it contains other text
            runbook_json = self._extract_json_from_response(response)
            if not runbook_json.strip():
                print(f"Error: AI response is empty or contains no JSON: {response[:200]}...", file=sys.stderr)
                # Fallback to evidence-only generation
                fallback_generator = EvidenceOnlyGenerator()
                return fallback_generator.generate(evidence, request_text)
            runbook = json.loads(runbook_json)
        except json.JSONDecodeError:
            print(f"Error: AI response is not valid JSON: {response[:200]}...", file=sys.stderr)
            # Fallback to evidence-only generation
            fallback_generator = EvidenceOnlyGenerator()
            return fallback_generator.generate(evidence, request_text)
        except Exception as e:
            print(f"Error processing AI response: {e}", file=sys.stderr)
            # Fallback to evidence-only generation
            fallback_generator = EvidenceOnlyGenerator()
            return fallback_generator.generate(evidence, request_text)

        # Validate the runbook structure
        if not isinstance(runbook, dict):
            print(f"Error: AI response is not a valid runbook object", file=sys.stderr)
            # Fallback to evidence-only generation
            fallback_generator = EvidenceOnlyGenerator()
            return fallback_generator.generate(evidence, request_text)

        # Ensure required fields are present
        if 'title' not in runbook:
            # Extract title from the request text if not provided by AI
            runbook['title'] = request_text[:100] if request_text else "Runbook from AI generation"

        # Generate a stable ID based on the title if not provided by AI
        if 'id' not in runbook:
            runbook['id'] = generate_runbook_id(runbook['title'])

        # Ensure timestamps are present
        now = datetime.now().isoformat()
        if 'created_at' not in runbook:
            runbook['created_at'] = now
        if 'updated_at' not in runbook:
            runbook['updated_at'] = now

        # Ensure steps are properly formatted
        if 'steps' not in runbook or not runbook['steps']:
            # Fallback to evidence-based steps if AI didn't generate any
            fallback_generator = EvidenceOnlyGenerator()
            fallback_runbook = fallback_generator.generate(evidence, request_text)
            runbook['steps'] = fallback_runbook.get('steps', [])

        return runbook

    def _create_runbook_generation_prompt(self, evidence: RunbookEvidence, request_text: str, actionable: bool = False) -> str:
        """Create a prompt for AI runbook generation."""
        evidence_summary = {
            'repo_root': evidence.repo_root,
            'commands_docs_count': len(evidence.commands_docs),
            'commands_docs': evidence.commands_docs,
            'help_available': evidence.help_text is not None,
            'help_text': evidence.help_text,
            'help_bin_path': evidence.help_bin_path,
            'warnings_count': len(evidence.warnings),
            'warnings': evidence.warnings
        }

        # Generate variable hints from evidence
        variable_hints = []
        if evidence.help_bin_path:
            variable_hints.append(f"<BSS_BIN>: {evidence.help_bin_path}")
        if evidence.repo_root:
            variable_hints.append(f"<REPO_ROOT>: (use this placeholder for repo root)")
        if evidence.commands_docs:
            # Infer docs directory from commands_docs filenames
            if evidence.commands_docs[0].get('filename'):
                # Assume docs are in docs/commands/ based on common patterns
                variable_hints.append(f"<DOCS_COMMANDS_DIR>: docs/commands/")

        # Additional hint about build directory (common in repos)
        variable_hints.append(f"<BUILD_DIR>: (use this placeholder for build output directory)")

        variable_hints_text = ""
        if variable_hints:
            variable_hints_text = "\n\nRESOLVED VARIABLE HINTS (use these in your commands):\n" + "\n".join(f"- {hint}" for hint in variable_hints)

        # Actionability requirement
        actionability_requirement = ""
        if actionable:
            actionability_requirement = """
        - CRITICAL: ALL steps MUST include executable commands
          - Each step MUST have either "command" (string) or "commands" (list of strings) field
          - Examples:
            * "command": "./build_maestro/bss --help"
            * "commands": ["grep -h '^##' docs/commands/*.md", "ls -la docs/"]
          - REJECT meta-steps like "review documentation", "analyze code", "organize"
            unless they include specific executable commands
          - Placeholders like <REPO_ROOT>, <BSS_BIN> are allowed in commands
        """

        prompt = f"""
        Create a structured runbook JSON based on the following request and evidence.

        REQUEST:
        {request_text}

        EVIDENCE:
        {json.dumps(evidence_summary, indent=2)}{variable_hints_text}

        INSTRUCTIONS:
        - Generate a complete runbook JSON object with the following structure:
          {{
            "id": "auto-generated",
            "title": "Short imperative title (under 100 chars)",
            "goal": "Detailed goal description",
            "prerequisites": ["list", "of", "prerequisites"],
            "steps": [
              {{
                "n": 1,
                "actor": "dev|user|system|ai",
                "action": "specific action to perform",
                "expected": "expected outcome",
                "command": "executable shell command (REQUIRED)",
                "details": "optional detailed description",
                "variants": ["optional", "variant", "descriptions"]
              }}
            ],
            "artifacts": [{{"path": "path/to/artifact", "purpose": "purpose of artifact"}}],
            "invariants": ["list", "of", "invariants"],
            "tags": ["list", "of", "tags"],
            "created_at": "auto-generated",
            "updated_at": "auto-generated"
          }}{actionability_requirement}
        - The runbook should reference actual commands and documentation from the evidence
        - Steps should be actionable and specific
        - Use the evidence to inform realistic steps and artifacts
        - Return ONLY the JSON object, no other text
        """

        return prompt

    def _extract_json_from_response(self, response: str) -> str:
        """Extract JSON from AI response that might contain other text."""
        # Look for JSON between ```json and ``` markers
        import re
        json_match = re.search(r'```json\s*\n(.*?)\n```', response, re.DOTALL)
        if json_match:
            return json_match.group(1).strip()

        # Look for JSON between ``` and ``` markers
        code_match = re.search(r'```\s*\n(.*?)\n```', response, re.DOTALL)
        if code_match:
            return code_match.group(1).strip()

        # If no markdown formatting, try to find JSON object directly
        # Find the first { and last }
        first_brace = response.find('{')
        last_brace = response.rfind('}')
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            return response[first_brace:last_brace+1]

        # If we can't extract JSON, return the original response
        return response


def format_ai_output_for_display(output_text: str, max_lines: int = 2000) -> str:
    """Format AI engine output for readable display in very verbose mode.

    Args:
        output_text: Raw output from the AI engine
        max_lines: Maximum number of lines to display before truncating

    Returns:
        Formatted string suitable for display
    """
    # Normalize line endings
    normalized_text = output_text.replace('\r\n', '\n')

    # Split into lines for potential truncation
    lines = normalized_text.split('\n')

    # Check if we need to truncate
    needs_truncation = len(lines) > max_lines

    # Take only the first max_lines if needed
    display_lines = lines[:max_lines] if needs_truncation else lines

    # Join the lines back together
    display_text = '\n'.join(display_lines)

    # Try to parse as JSON for pretty formatting
    try:
        parsed_json = json.loads(display_text)
        # Pretty print JSON with indentation
        formatted_text = json.dumps(parsed_json, indent=2, ensure_ascii=False)

        if needs_truncation:
            formatted_text += f"\n\n(... output truncated; full output exceeds {max_lines} lines)"

        return formatted_text
    except json.JSONDecodeError:
        # If not JSON, try to parse as JSONL (JSON Lines)
        try:
            # Check if it looks like JSONL (multiple JSON objects separated by newlines)
            json_objects = []
            for line in display_lines:
                line = line.strip()
                if line.startswith('{') and line.endswith('}'):
                    json_objects.append(json.loads(line))

            if json_objects:
                # Format as numbered list of JSON objects
                formatted_parts = []
                for i, obj in enumerate(json_objects, 1):
                    formatted_parts.append(f"{i}. {json.dumps(obj, indent=2)}")

                formatted_text = '\n'.join(formatted_parts)

                if needs_truncation:
                    formatted_text += f"\n\n(... output truncated; full output exceeds {max_lines} lines)"

                return formatted_text
        except json.JSONDecodeError:
            pass  # Continue to plain text formatting if JSONL parsing fails

    # If not JSON or JSONL, return as plain text with normalization
    # Strip trailing whitespace from each line
    normalized_lines = [line.rstrip() for line in display_lines]
    formatted_text = '\n'.join(normalized_lines)

    if needs_truncation:
        formatted_text += f"\n\n(... output truncated; full output exceeds {max_lines} lines)"

    return formatted_text


def validate_runbook_schema(runbook: Dict[str, Any]) -> List[str]:
    """Validate runbook against schema requirements."""
    errors = []

    # Required fields at the top level
    required_fields = ['id', 'title', 'goal', 'steps']
    for field in required_fields:
        if field not in runbook:
            errors.append(f"Missing required field: {field}")

    # Validate field types
    if 'id' in runbook and not isinstance(runbook['id'], str):
        errors.append("id must be a string")

    if 'title' in runbook and not isinstance(runbook['title'], str):
        errors.append("title must be a string")

    if 'goal' in runbook and not isinstance(runbook['goal'], str):
        errors.append("goal must be a string")

    # Validate optional fields if present
    if 'prerequisites' in runbook and not isinstance(runbook['prerequisites'], list):
        errors.append("prerequisites must be a list if present")

    if 'artifacts' in runbook and not isinstance(runbook['artifacts'], list):
        errors.append("artifacts must be a list if present")

    if 'invariants' in runbook and not isinstance(runbook['invariants'], list):
        errors.append("invariants must be a list if present")

    if 'tags' in runbook and not isinstance(runbook['tags'], list):
        errors.append("tags must be a list if present")

    # Validate steps
    if 'steps' in runbook:
        if not isinstance(runbook['steps'], list):
            errors.append("Steps must be a list")
        elif len(runbook['steps']) == 0:
            errors.append("Steps list cannot be empty")
        else:
            for i, step in enumerate(runbook['steps']):
                if not isinstance(step, dict):
                    errors.append(f"Step {i} must be an object")
                    continue

                # Required fields in each step
                step_required = ['n', 'actor', 'action', 'expected']
                for field in step_required:
                    if field not in step:
                        errors.append(f"Step {i} missing required field: {field}")

                # Validate step field types
                if 'n' in step and not isinstance(step['n'], int):
                    errors.append(f"Step {i} n must be an integer")

                if 'actor' in step and not isinstance(step['actor'], str):
                    errors.append(f"Step {i} actor must be a string")

                if 'action' in step and not isinstance(step['action'], str):
                    errors.append(f"Step {i} action must be a string")

                if 'expected' in step and not isinstance(step['expected'], str):
                    errors.append(f"Step {i} expected must be a string")

                if 'details' in step and not isinstance(step['details'], str):
                    errors.append(f"Step {i} details must be a string if present")

                if 'variants' in step and not isinstance(step['variants'], list):
                    errors.append(f"Step {i} variants must be a list if present")

                # Normalize command by stripping leading $ and whitespace (for backward compatibility)
                if 'cmd' in step and isinstance(step['cmd'], str):
                    step['cmd'] = step['cmd'].strip().lstrip('$').strip()

    # Validate artifacts if present
    if 'artifacts' in runbook:
        for i, artifact in enumerate(runbook['artifacts']):
            if not isinstance(artifact, dict):
                errors.append(f"Artifact {i} must be an object")
                continue

            if 'path' not in artifact:
                errors.append(f"Artifact {i} missing required field: path")

            if 'purpose' not in artifact:
                errors.append(f"Artifact {i} missing required field: purpose")

    # Validate prerequisites if present
    if 'prerequisites' in runbook:
        for i, prereq in enumerate(runbook['prerequisites']):
            if not isinstance(prereq, str):
                errors.append(f"Prerequisite {i} must be a string")

    # Validate invariants if present
    if 'invariants' in runbook:
        for i, invariant in enumerate(runbook['invariants']):
            if not isinstance(invariant, str):
                errors.append(f"Invariant {i} must be a string")

    # Validate tags if present
    if 'tags' in runbook:
        for i, tag in enumerate(runbook['tags']):
            if not isinstance(tag, str):
                errors.append(f"Tag {i} must be a string")

    return errors


def validate_runbook_actionability(runbook: Dict[str, Any]) -> List[str]:
    """
    Validate that a runbook meets actionability requirements.

    An actionable runbook must have executable steps (command or commands field).
    Meta-steps without executable directives are rejected.

    Args:
        runbook: The runbook dictionary to validate

    Returns:
        List of actionability errors (empty if valid)
    """
    errors = []

    steps = runbook.get('steps', [])
    if not steps:
        # Empty steps already caught by schema validation
        return errors

    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            # Not a dict - already caught by schema validation
            continue

        # Check if step has command or commands field
        has_command = 'command' in step and isinstance(step['command'], str) and step['command'].strip()
        has_commands = 'commands' in step and isinstance(step['commands'], list) and len(step['commands']) > 0

        if not (has_command or has_commands):
            # Check if this looks like a meta-step
            action = step.get('action', '')
            meta_keywords = [
                'review', 'analyze', 'parse', 'organize', 'create outline',
                'group', 'categorize', 'document', 'understand', 'study',
                'read', 'examine', 'investigate', 'explore'
            ]

            is_meta_step = any(keyword in action.lower() for keyword in meta_keywords)

            if is_meta_step:
                errors.append(
                    f"Step {step.get('n', i+1)} is a meta-step without executable command: '{action}' "
                    f"(missing 'command' or 'commands' field)"
                )
            else:
                errors.append(
                    f"Step {step.get('n', i+1)} missing executable command: '{action}' "
                    f"(needs 'command' or 'commands' field)"
                )

    return errors


def create_runbook_from_freeform(text: str, verbose: bool = False) -> Optional[Dict[str, Any]]:
    """Create a runbook from freeform text using AI (placeholder implementation)."""
    # This is a placeholder implementation - in the real implementation,
    # this would call the AI to generate the runbook from the freeform text
    # For now, we'll create a more sophisticated runbook based on the input text

    # Generate a title from the first part of the text
    lines = text.strip().split('\n')
    title = lines[0][:100] if lines[0] else "Runbook from freeform text"

    # Generate a deterministic ID
    runbook_id = generate_runbook_id(title)

    # Gather repo evidence if available
    repo_evidence = gather_repo_evidence()

    # Create a more detailed prompt for the AI (in a real implementation)
    # For now, we'll create a structured runbook based on the input
    runbook = {
        'id': runbook_id,
        'title': title,
        'goal': text[:500],  # Use first 500 chars as goal
        'prerequisites': [],
        'steps': [
            {
                'cmd': 'echo "Implement actual steps based on requirements"',
                'expect': 'Command executes successfully',
                'notes': f'Original input: {text[:200]}{"..." if len(text) > 200 else ""}'
            }
        ],
        'artifacts': [],
        'invariants': [],
        'tags': ['generated'],
        'created_at': datetime.now().isoformat(),
        'updated_at': datetime.now().isoformat()
    }

    # Add repo evidence to the runbook if available
    if repo_evidence:
        runbook['repo_evidence'] = repo_evidence

    if verbose:
        print(f"Generated runbook ID: {runbook_id}")
        print(f"Repo evidence included: {bool(repo_evidence)}")

    return runbook


def gather_repo_evidence() -> Dict[str, Any]:
    """Gather repo evidence to include in the AI prompt."""
    evidence = {}

    # Include CLI surface summary if available
    try:
        # Look for CLI surface information in the repo
        cli_surface_path = Path.cwd() / "docs" / "maestro" / "cli_surface.json"
        if cli_surface_path.exists():
            with open(cli_surface_path, 'r') as f:
                evidence['cli_surface'] = json.load(f)
    except Exception:
        pass  # Ignore if CLI surface info is not available

    # Include repo model summary if available
    try:
        # Look for repo model information
        repo_model_path = Path.cwd() / "docs" / "maestro" / "repo_model.json"
        if repo_model_path.exists():
            with open(repo_model_path, 'r') as f:
                repo_model = json.load(f)
                evidence['repo_model'] = {
                    'packages_count': len(repo_model.get('packages', [])),
                    'assemblies_count': len(repo_model.get('assemblies', [])),
                    'has_virtual_packages': repo_model.get('has_virtual_packages', False)
                }
    except Exception:
        pass  # Ignore if repo model info is not available

    # Include basic repo information
    try:
        import subprocess
        # Get git information if in a git repo
        try:
            git_status = subprocess.run(['git', 'status'], capture_output=True, text=True, cwd=Path.cwd())
            if git_status.returncode == 0:
                evidence['git'] = {
                    'is_git_repo': True,
                    'branch': subprocess.run(['git', 'branch', '--show-current'], capture_output=True, text=True, cwd=Path.cwd()).stdout.strip(),
                    'has_uncommitted_changes': 'nothing to commit' not in git_status.stdout
                }
        except:
            evidence['git'] = {'is_git_repo': False}
    except Exception:
        pass  # Ignore if git info is not available

    return evidence


def save_runbook_with_update_semantics(runbook: Dict[str, Any]) -> None:
    """Save runbook with update semantics (replace if exists, add if new)."""
    _ensure_runbook_storage()

    # Save the runbook file
    runbook_path = _get_runbook_storage_path() / "items" / f"{runbook['id']}.json"
    with open(runbook_path, 'w') as f:
        json.dump(runbook, f, indent=2)

    # Update the index
    index = _load_index()
    existing_entry = None
    for i, entry in enumerate(index):
        if entry['id'] == runbook['id']:
            existing_entry = i
            break

    # Create or update index entry
    index_entry = {
        'id': runbook['id'],
        'title': runbook['title'],
        'tags': runbook.get('tags', []),
        'status': runbook.get('status', 'proposed'),
        'updated_at': runbook['updated_at']
    }

    if existing_entry is not None:
        # Update existing entry
        index[existing_entry] = index_entry
    else:
        # Add new entry
        index.append(index_entry)

    # Save updated index
    _save_index(index)


def add_runbook_parser(subparsers: Any) -> None:
    """Add runbook command parser."""
    runbook_parser = subparsers.add_parser(
        'runbook',
        aliases=['runba', 'rb'],
        help='Runbook-first bootstrap before workflow',
        description='Manage runbook entries as first-class project assets. '
                    'Runbooks provide a narrative-first modeling layer before formalization.'
    )

    # Add subparsers for runbook command
    runbook_subparsers = runbook_parser.add_subparsers(dest='runbook_subcommand', help='Runbook subcommands')

    # List command
    list_parser = runbook_subparsers.add_parser('list', aliases=['ls'], help='List all runbooks')
    list_parser.add_argument('--status', choices=['proposed', 'approved', 'deprecated'], help='Filter by status')
    list_parser.add_argument('--scope', choices=['product', 'user', 'manager', 'ui', 'code', 'reverse_engineering'], help='Filter by scope')
    list_parser.add_argument('--tag', help='Filter by tag')
    list_parser.add_argument('--archived', action='store_true', help='List archived items instead of active')
    list_parser.add_argument('--type', choices=['markdown', 'json', 'all'], default='all', help='Filter by type (for archived items)')

    # Show command
    show_parser = runbook_subparsers.add_parser('show', aliases=['sh'], help='Show a specific runbook')
    show_parser.add_argument('id', help='ID of the runbook to show')
    show_parser.add_argument('--archived', action='store_true', help='Show archived item')
    show_parser.add_argument('--json', action='store_true', help='Show raw JSON output')

    # Add command
    add_parser = runbook_subparsers.add_parser('add', aliases=['new'], help='Create a new runbook')
    add_parser.add_argument('--title', required=True, help='Title of the runbook')
    add_parser.add_argument('--scope', choices=['product', 'user', 'manager', 'ui', 'code', 'reverse_engineering'],
                           default='product', help='Scope of the runbook (default: product)')
    add_parser.add_argument('--tag', action='append', help='Add tags (can be specified multiple times)')
    add_parser.add_argument('--source-program', help='Source program name/version (for reverse engineering)')
    add_parser.add_argument('--target-project', help='Target project name')

    # Edit command
    edit_parser = runbook_subparsers.add_parser('edit', aliases=['e'], help='Edit a runbook')
    edit_parser.add_argument('id', help='ID of the runbook to edit')
    edit_parser.add_argument('--title', help='New title')
    edit_parser.add_argument('--status', choices=['proposed', 'approved', 'deprecated'], help='New status')
    edit_parser.add_argument('--scope', choices=['product', 'user', 'manager', 'ui', 'code', 'reverse_engineering'], help='New scope')
    edit_parser.add_argument('--tag', action='append', help='Add tags (can be specified multiple times)')

    # Remove command
    rm_parser = runbook_subparsers.add_parser('rm', aliases=['remove', 'delete'], help='Delete a runbook')
    rm_parser.add_argument('id', help='ID of the runbook to delete')
    rm_parser.add_argument('--force', '-f', action='store_true', help='Skip confirmation')

    # Step add command
    step_add_parser = runbook_subparsers.add_parser('step-add', aliases=['sa'], help='Add a step to a runbook')
    step_add_parser.add_argument('id', help='ID of the runbook')
    step_add_parser.add_argument('--actor', required=True, help='Actor performing the step (e.g., user, manager, system, ai)')
    step_add_parser.add_argument('--action', required=True, help='Short action description')
    step_add_parser.add_argument('--expected', required=True, help='Expected outcome')
    step_add_parser.add_argument('--details', help='Multi-line detailed description')
    step_add_parser.add_argument('--variants', action='append', help='Variant descriptions (can be specified multiple times)')

    # Step edit command
    step_edit_parser = runbook_subparsers.add_parser('step-edit', aliases=['se'], help='Edit a step in a runbook')
    step_edit_parser.add_argument('id', help='ID of the runbook')
    step_edit_parser.add_argument('n', type=int, help='Step number to edit')
    step_edit_parser.add_argument('--actor', help='New actor')
    step_edit_parser.add_argument('--action', help='New action')
    step_edit_parser.add_argument('--expected', help='New expected outcome')
    step_edit_parser.add_argument('--details', help='New details')

    # Step rm command
    step_rm_parser = runbook_subparsers.add_parser('step-rm', aliases=['sr'], help='Remove a step from a runbook')
    step_rm_parser.add_argument('id', help='ID of the runbook')
    step_rm_parser.add_argument('n', type=int, help='Step number to remove')

    # Step renumber command
    step_renumber_parser = runbook_subparsers.add_parser('step-renumber', aliases=['srn'], help='Renumber steps in a runbook')
    step_renumber_parser.add_argument('id', help='ID of the runbook')

    # Export command
    export_parser = runbook_subparsers.add_parser('export', aliases=['exp'], help='Export a runbook')
    export_parser.add_argument('id', help='ID of the runbook to export')
    export_parser.add_argument('--format', choices=['md', 'puml'], default='md', help='Export format (default: md)')
    export_parser.add_argument('--out', help='Output file path (default: docs/maestro/runbooks/exports/<id>.<format>)')

    # Render command (optional PUML to SVG)
    render_parser = runbook_subparsers.add_parser('render', aliases=['rnd'], help='Render a runbook PUML to SVG')
    render_parser.add_argument('id', help='ID of the runbook to render')
    render_parser.add_argument('--out', help='Output SVG file path')

    # Discuss command
    discuss_parser = runbook_subparsers.add_parser('discuss', aliases=['d'], help='Discuss runbook with AI (placeholder)')
    discuss_parser.add_argument('id', help='ID of the runbook to discuss')

    # Resolve command
    resolve_parser = runbook_subparsers.add_parser('resolve', aliases=['res'], help='Resolve freeform text to structured runbook JSON')
    resolve_parser.add_argument('text', nargs='?', help='Freeform text to convert to runbook')
    resolve_parser.add_argument('-v', '--verbose', action='store_true', help='Show prompt hash, engine, evidence summary, validation summary')
    resolve_parser.add_argument('-vv', '--very-verbose', action='store_true', help='Also print resolved AI prompt and pretty engine output')
    resolve_parser.add_argument('-e', '--eval', action='store_true', help='Read freeform input from stdin instead of positional argument')
    resolve_parser.add_argument('--no-evidence', action='store_true', help='Skip repo evidence collection; only use provided text')
    resolve_parser.add_argument('--evidence-pack', help='Use existing evidence pack ID (from maestro repo evidence pack --save)')
    resolve_parser.add_argument('--help-bin', help='Force a specific binary path for --help collection')
    resolve_parser.add_argument('--commands-dir', help='Override docs/commands directory path')
    resolve_parser.add_argument('--engine', help='Engine to use (e.g., claude, qwen, codex, gemini)')
    resolve_parser.add_argument('--evidence-only', action='store_true', help='Use deterministic evidence compilation instead of AI')
    resolve_parser.add_argument('--name', help='Custom name for the runbook (overrides AI-generated title)')
    resolve_parser.add_argument('--dry-run', action='store_true', help='Show what would be created without saving')
    resolve_parser.add_argument('--actionable', action='store_true', help='Enforce actionability: all steps must have executable commands (fallback to WorkGraph on failure)')

    # Archive command
    archive_parser = runbook_subparsers.add_parser('archive', help='Archive a runbook (markdown or JSON)')
    archive_parser.add_argument('id_or_path', help='Runbook ID or file path')
    archive_parser.add_argument('--reason', help='Reason for archiving')

    # Restore command
    restore_parser = runbook_subparsers.add_parser('restore', help='Restore an archived runbook')
    restore_parser.add_argument('archive_id', help='Archive ID to restore')

    runbook_parser.set_defaults(func=handle_runbook_command)


def handle_runbook_command(args: argparse.Namespace) -> None:
    """Handle the runbook command."""
    if not hasattr(args, 'runbook_subcommand') or args.runbook_subcommand is None:
        print("Usage: maestro runbook [list|show|add|edit|rm|step-add|step-edit|step-rm|step-renumber|export|render|discuss] [options]")
        print("\nRunbook-first bootstrap - manage narrative-style procedural descriptions before workflow formalization.")
        return

    if args.runbook_subcommand in ['list', 'ls']:
        handle_runbook_list(args)
    elif args.runbook_subcommand in ['show', 'sh']:
        handle_runbook_show(args)
    elif args.runbook_subcommand in ['add', 'new']:
        handle_runbook_add(args)
    elif args.runbook_subcommand in ['edit', 'e']:
        handle_runbook_edit(args)
    elif args.runbook_subcommand in ['rm', 'remove', 'delete']:
        handle_runbook_rm(args)
    elif args.runbook_subcommand in ['step-add', 'sa']:
        handle_step_add(args)
    elif args.runbook_subcommand in ['step-edit', 'se']:
        handle_step_edit(args)
    elif args.runbook_subcommand in ['step-rm', 'sr']:
        handle_step_rm(args)
    elif args.runbook_subcommand in ['step-renumber', 'srn']:
        handle_step_renumber(args)
    elif args.runbook_subcommand in ['export', 'exp']:
        handle_runbook_export(args)
    elif args.runbook_subcommand in ['render', 'rnd']:
        handle_runbook_render(args)
    elif args.runbook_subcommand in ['discuss', 'd']:
        handle_runbook_discuss(args)
    elif args.runbook_subcommand in ['resolve', 'res']:
        handle_runbook_resolve(args)
    elif args.runbook_subcommand == 'archive':
        handle_runbook_archive(args)
    elif args.runbook_subcommand == 'restore':
        handle_runbook_restore(args)
    else:
        print(f"Unknown runbook subcommand: {args.runbook_subcommand}")


def _get_runbook_storage_path() -> Path:
    """Get the base path for runbook storage."""
    return get_docs_root() / "docs" / "maestro" / "runbooks"


def _ensure_runbook_storage() -> None:
    """Ensure runbook storage directories exist."""
    storage_path = _get_runbook_storage_path()
    storage_path.mkdir(parents=True, exist_ok=True)
    (storage_path / "items").mkdir(exist_ok=True)
    (storage_path / "exports").mkdir(exist_ok=True)


def _load_index() -> List[Dict[str, Any]]:
    """Load the runbook index, rebuilding from filesystem if missing or stale."""
    index_path = _get_runbook_storage_path() / "index.json"
    runbooks_dir = _get_runbook_storage_path() / "items"

    # If index doesn't exist, rebuild it from filesystem
    if not index_path.exists():
        return _rebuild_index_from_filesystem()

    # Load existing index
    with open(index_path, 'r') as f:
        index = json.load(f)

    # Check for stale entries (files that no longer exist) and rebuild if needed
    stale_entries = []
    for i, entry in enumerate(index):
        runbook_path = runbooks_dir / f"{entry['id']}.json"
        if not runbook_path.exists():
            stale_entries.append(i)

    # If there are stale entries, rebuild the index
    if stale_entries:
        return _rebuild_index_from_filesystem()

    return index


def _rebuild_index_from_filesystem() -> List[Dict[str, Any]]:
    """Rebuild the runbook index from the filesystem."""
    runbooks_dir = _get_runbook_storage_path() / "items"
    runbooks_dir.mkdir(parents=True, exist_ok=True)

    index = []
    for runbook_file in runbooks_dir.glob("*.json"):
        runbook_id = runbook_file.stem
        runbook = _load_runbook(runbook_id)
        if runbook:
            index_entry = {
                'id': runbook['id'],
                'title': runbook['title'],
                'tags': runbook.get('tags', []),
                'status': runbook.get('status', 'proposed'),
                'updated_at': runbook.get('updated_at', datetime.now().isoformat())
            }
            index.append(index_entry)

    # Save the rebuilt index
    _save_index(index)
    return index


def _save_index(index: List[Dict[str, Any]]) -> None:
    """Save the runbook index atomically."""
    import tempfile
    _ensure_runbook_storage()
    index_path = _get_runbook_storage_path() / "index.json"

    # Write to a temporary file first
    with tempfile.NamedTemporaryFile(mode='w', dir=index_path.parent, delete=False, suffix='.tmp') as tmp_file:
        json.dump(index, tmp_file, indent=2)
        tmp_path = Path(tmp_file.name)

    # Atomically move the temporary file to the target location
    tmp_path.replace(index_path)


def _load_runbook(runbook_id: str) -> Optional[Dict[str, Any]]:
    """Load a runbook by ID."""
    runbook_path = _get_runbook_storage_path() / "items" / f"{runbook_id}.json"
    if not runbook_path.exists():
        return None
    with open(runbook_path, 'r') as f:
        return json.load(f)


def _save_runbook(runbook: Dict[str, Any]) -> None:
    """Save a runbook atomically."""
    import tempfile
    _ensure_runbook_storage()
    runbook_id = runbook['id']
    runbook_path = _get_runbook_storage_path() / "items" / f"{runbook_id}.json"

    # Write to a temporary file first
    with tempfile.NamedTemporaryFile(mode='w', dir=runbook_path.parent, delete=False, suffix='.tmp') as tmp_file:
        json.dump(runbook, tmp_file, indent=2)
        tmp_path = Path(tmp_file.name)

    # Atomically move the temporary file to the target location
    tmp_path.replace(runbook_path)


def _generate_runbook_id(title: str) -> str:
    """Generate a runbook ID from title."""
    # Simple ID generation: lowercase, replace spaces with dashes, limit length
    base_id = title.lower().replace(' ', '-')[:30]
    # Remove special characters
    base_id = ''.join(c for c in base_id if c.isalnum() or c == '-')

    # Check for conflicts and add suffix if needed
    index = _load_index()
    existing_ids = {item['id'] for item in index}

    if base_id not in existing_ids:
        return base_id

    # Add numeric suffix
    counter = 1
    while f"{base_id}-{counter}" in existing_ids:
        counter += 1
    return f"{base_id}-{counter}"


def handle_runbook_list(args: argparse.Namespace) -> None:
    """Handle the runbook list command."""
    # Check if we should list archived runbooks
    if hasattr(args, 'archived') and args.archived:
        # List archived runbooks instead
        from maestro.archive.runbook_archive import list_archived_runbooks

        type_filter = getattr(args, 'type', 'all') if hasattr(args, 'type') else 'all'
        if type_filter == 'all':
            type_filter = None  # None means all types

        archived_entries = list_archived_runbooks(type_filter=type_filter)

        if not archived_entries:
            print("No archived runbooks found.")
            return

        print(f"Found {len(archived_entries)} archived runbook(s):\n")
        for entry in archived_entries:
            print(f"  {entry.archive_id:<30} [{entry.type:>15}] {entry.archived_at}")
            print(f"  {'':30} original: {entry.original_path}")
            if entry.reason:
                print(f"  {'':30} reason: {entry.reason}")
            print()
        return

    # List active runbooks
    index = _load_index()

    # Apply filters
    if hasattr(args, 'status') and args.status:
        index = [item for item in index if item.get('status') == args.status]
    if hasattr(args, 'scope') and args.scope:
        index = [item for item in index if item.get('scope') == args.scope]
    if hasattr(args, 'tag') and args.tag:
        index = [item for item in index if args.tag in item.get('tags', [])]

    if not index:
        print("No runbooks found.")
        return

    print(f"Found {len(index)} runbook(s):\n")
    for item in index:
        # Load full runbook to get scope (index doesn't store it)
        runbook = _load_runbook(item['id'])
        tags_str = ', '.join(item.get('tags', [])) if item.get('tags') else 'none'
        print(f"  {item['id']:<30} [{item.get('status', 'proposed'):>10}] {item['title']}")
        scope = runbook.get('scope', 'product') if runbook else 'product'
        print(f"  {'':30} scope: {scope:<20} tags: {tags_str}")
        print(f"  {'':30} updated: {item.get('updated_at', 'N/A')}")
        print()


def handle_runbook_show(args: argparse.Namespace) -> None:
    """Handle the runbook show command."""
    # Check if we should show archived runbook
    if hasattr(args, 'archived') and args.archived:
        from maestro.archive.runbook_archive import find_archive_entry, RestoreError
        try:
            # Try to find the archived runbook
            entry = find_archive_entry(args.id)
            if not entry:
                print(f"Error: Archived runbook '{args.id}' not found.")
                return

            # For archived runbook, we'll just show the archive entry details
            print(f"Archived Runbook: {entry.archive_id}")
            print(f"Type: {entry.type}")
            print(f"Original Path: {entry.original_path}")
            print(f"Archived At: {entry.archived_at}")
            print(f"User: {entry.user}")
            if entry.reason:
                print(f"Reason: {entry.reason}")
            if entry.git_head:
                print(f"Git Head: {entry.git_head}")
        except RestoreError as e:
            print(f"Error: {e}")
        return

    runbook = _load_runbook(args.id)
    if not runbook:
        print(f"Error: Runbook '{args.id}' not found.")
        return

    # If --json flag is set, output raw JSON
    if hasattr(args, 'json') and args.json:
        print(json.dumps(runbook, indent=2))
        return

    # Otherwise, show human-readable format
    print(f"Runbook: {runbook['title']}")
    print(f"ID: {runbook['id']}")
    print(f"Status: {runbook.get('status', 'proposed')}")
    print(f"Scope: {runbook.get('scope', 'product')}")
    if runbook.get('tags'):
        print(f"Tags: {', '.join(runbook['tags'])}")
    print(f"Created: {runbook.get('created_at', 'N/A')}")
    print(f"Updated: {runbook.get('updated_at', 'N/A')}")

    context = runbook.get('context', {})
    if context.get('source_program'):
        print(f"Source Program: {context['source_program']}")
    if context.get('target_project'):
        print(f"Target Project: {context['target_project']}")

    steps = runbook.get('steps', [])
    if steps:
        print(f"\nSteps ({len(steps)}):")
        for step in steps:
            # Handle backward compatibility for old step schema
            step_number = step.get('n', 'N/A')
            actor = step.get('actor', 'N/A')
            action = step.get('action', 'N/A')
            expected = step.get('expected', step.get('expect', 'N/A'))  # 'expect' for backward compatibility

            print(f"  {step_number}. [{actor}] {action}")
            print(f"     Expected: {expected}")
            if step.get('details'):
                print(f"     Details: {step['details']}")
            if step.get('variants'):
                print(f"     Variants: {', '.join(step['variants'])}")
    else:
        print("\nSteps: none")

    links = runbook.get('links', {})
    if links:
        if links.get('workflows'):
            print(f"\nLinked Workflows: {', '.join(links['workflows'])}")
        if links.get('issues'):
            print(f"Linked Issues: {', '.join(links['issues'])}")
        if links.get('tasks'):
            print(f"Linked Tasks: {', '.join(links['tasks'])}")


def handle_runbook_add(args: argparse.Namespace) -> None:
    """Handle the runbook add command."""
    runbook_id = _generate_runbook_id(args.title)
    now = datetime.now().isoformat()

    runbook = {
        'id': runbook_id,
        'title': args.title,
        'status': 'proposed',
        'scope': args.scope if hasattr(args, 'scope') and args.scope else 'product',
        'tags': args.tag if hasattr(args, 'tag') and args.tag else [],
        'context': {},
        'steps': [],
        'links': {
            'workflows': [],
            'issues': [],
            'tasks': []
        },
        'created_at': now,
        'updated_at': now
    }

    if hasattr(args, 'source_program') and args.source_program:
        runbook['context']['source_program'] = args.source_program
    if hasattr(args, 'target_project') and args.target_project:
        runbook['context']['target_project'] = args.target_project

    # Save runbook
    _save_runbook(runbook)

    # Update index
    index = _load_index()
    index.append({
        'id': runbook_id,
        'title': args.title,
        'tags': runbook['tags'],
        'status': 'proposed',
        'updated_at': now
    })
    _save_index(index)

    print(f"Created runbook: {runbook_id}")
    print(f"  Title: {args.title}")
    print(f"  Scope: {runbook['scope']}")


def handle_runbook_edit(args: argparse.Namespace) -> None:
    """Handle the runbook edit command."""
    runbook = _load_runbook(args.id)
    if not runbook:
        print(f"Error: Runbook '{args.id}' not found.")
        return

    # Update fields
    changed = False
    if hasattr(args, 'title') and args.title:
        runbook['title'] = args.title
        changed = True
    if hasattr(args, 'status') and args.status:
        runbook['status'] = args.status
        changed = True
    if hasattr(args, 'scope') and args.scope:
        runbook['scope'] = args.scope
        changed = True
    if hasattr(args, 'tag') and args.tag:
        runbook['tags'] = list(set(runbook.get('tags', []) + args.tag))
        changed = True

    if not changed:
        print("No changes specified.")
        return

    # Update timestamp
    runbook['updated_at'] = datetime.now().isoformat()

    # Save runbook
    _save_runbook(runbook)

    # Update index
    index = _load_index()
    for item in index:
        if item['id'] == args.id:
            item['title'] = runbook['title']
            item['status'] = runbook.get('status', 'proposed')
            item['tags'] = runbook.get('tags', [])
            item['updated_at'] = runbook['updated_at']
            break
    _save_index(index)

    print(f"Updated runbook: {args.id}")


def handle_runbook_rm(args: argparse.Namespace) -> None:
    """Handle the runbook rm command."""
    runbook = _load_runbook(args.id)
    if not runbook:
        print(f"Error: Runbook '{args.id}' not found.")
        return

    # Confirm unless --force
    if not (hasattr(args, 'force') and args.force):
        response = input(f"Delete runbook '{args.id}' ({runbook['title']})? [y/N]: ")
        if response.lower() != 'y':
            print("Cancelled.")
            return

    # Delete file
    runbook_path = _get_runbook_storage_path() / "items" / f"{args.id}.json"
    runbook_path.unlink()

    # Update index
    index = _load_index()
    index = [item for item in index if item['id'] != args.id]
    _save_index(index)

    print(f"Deleted runbook: {args.id}")


def handle_step_add(args: argparse.Namespace) -> None:
    """Handle the step add command."""
    runbook = _load_runbook(args.id)
    if not runbook:
        print(f"Error: Runbook '{args.id}' not found.")
        return

    steps = runbook.get('steps', [])
    next_n = len(steps) + 1

    step = {
        'n': next_n,
        'actor': args.actor,
        'action': args.action,
        'expected': args.expected
    }

    if hasattr(args, 'details') and args.details:
        step['details'] = args.details
    if hasattr(args, 'variants') and args.variants:
        step['variants'] = args.variants

    steps.append(step)
    runbook['steps'] = steps
    runbook['updated_at'] = datetime.now().isoformat()

    _save_runbook(runbook)

    # Update index timestamp
    index = _load_index()
    for item in index:
        if item['id'] == args.id:
            item['updated_at'] = runbook['updated_at']
            break
    _save_index(index)

    print(f"Added step {next_n} to runbook {args.id}")


def handle_step_edit(args: argparse.Namespace) -> None:
    """Handle the step edit command."""
    runbook = _load_runbook(args.id)
    if not runbook:
        print(f"Error: Runbook '{args.id}' not found.")
        return

    steps = runbook.get('steps', [])
    step = next((s for s in steps if s.get('n') == args.n), None)
    if not step:
        print(f"Error: Step {args.n} not found in runbook {args.id}.")
        return

    # Update fields
    changed = False
    if hasattr(args, 'actor') and args.actor:
        step['actor'] = args.actor
        changed = True
    if hasattr(args, 'action') and args.action:
        step['action'] = args.action
        changed = True
    if hasattr(args, 'expected') and args.expected:
        step['expected'] = args.expected
        changed = True
    if hasattr(args, 'details') and args.details:
        step['details'] = args.details
        changed = True

    if not changed:
        print("No changes specified.")
        return

    runbook['updated_at'] = datetime.now().isoformat()
    _save_runbook(runbook)

    # Update index timestamp
    index = _load_index()
    for item in index:
        if item['id'] == args.id:
            item['updated_at'] = runbook['updated_at']
            break
    _save_index(index)

    print(f"Updated step {args.n} in runbook {args.id}")


def handle_step_rm(args: argparse.Namespace) -> None:
    """Handle the step rm command."""
    runbook = _load_runbook(args.id)
    if not runbook:
        print(f"Error: Runbook '{args.id}' not found.")
        return

    steps = runbook.get('steps', [])
    step = next((s for s in steps if s.get('n') == args.n), None)
    if not step:
        print(f"Error: Step {args.n} not found in runbook {args.id}.")
        return

    # Remove step
    steps = [s for s in steps if s.get('n') != args.n]

    # Renumber remaining steps, handling backward compatibility
    def sort_key(step):
        return step.get('n', float('inf'))  # Put steps without 'n' at the end

    sorted_steps = sorted(steps, key=sort_key)

    for i, s in enumerate(sorted_steps, start=1):
        s['n'] = i

    runbook['steps'] = steps
    runbook['updated_at'] = datetime.now().isoformat()
    _save_runbook(runbook)

    # Update index timestamp
    index = _load_index()
    for item in index:
        if item['id'] == args.id:
            item['updated_at'] = runbook['updated_at']
            break
    _save_index(index)

    print(f"Removed step {args.n} from runbook {args.id} (steps renumbered)")


def handle_step_renumber(args: argparse.Namespace) -> None:
    """Handle the step renumber command."""
    runbook = _load_runbook(args.id)
    if not runbook:
        print(f"Error: Runbook '{args.id}' not found.")
        return

    steps = runbook.get('steps', [])

    # Renumber steps sequentially, handling backward compatibility
    # Sort by 'n' if it exists, otherwise use the original order
    def sort_key(step):
        return step.get('n', float('inf'))  # Put steps without 'n' at the end

    sorted_steps = sorted(steps, key=sort_key)

    for i, step in enumerate(sorted_steps, start=1):
        step['n'] = i

    runbook['steps'] = steps
    runbook['updated_at'] = datetime.now().isoformat()
    _save_runbook(runbook)

    # Update index timestamp
    index = _load_index()
    for item in index:
        if item['id'] == args.id:
            item['updated_at'] = runbook['updated_at']
            break
    _save_index(index)

    print(f"Renumbered {len(steps)} steps in runbook {args.id}")


def handle_runbook_export(args: argparse.Namespace) -> None:
    """Handle the runbook export command."""
    runbook = _load_runbook(args.id)
    if not runbook:
        print(f"Error: Runbook '{args.id}' not found.")
        return

    # Determine output path
    if hasattr(args, 'out') and args.out:
        out_path = Path(args.out)
    else:
        _ensure_runbook_storage()
        out_path = _get_runbook_storage_path() / "exports" / f"{args.id}.{args.format}"

    out_path.parent.mkdir(parents=True, exist_ok=True)

    if args.format == 'md':
        content = _export_runbook_md(runbook)
    elif args.format == 'puml':
        content = _export_runbook_puml(runbook)
    else:
        print(f"Error: Unknown format '{args.format}'")
        return

    with open(out_path, 'w') as f:
        f.write(content)

    print(f"Exported runbook {args.id} to {out_path}")


def _export_runbook_md(runbook: Dict[str, Any]) -> str:
    """Export runbook to Markdown format."""
    lines = []
    lines.append(f"# Runbook: {runbook['title']}\n")
    lines.append(f"**ID:** {runbook['id']}  ")
    lines.append(f"**Status:** {runbook.get('status', 'proposed')}  ")
    lines.append(f"**Scope:** {runbook.get('scope', 'product')}  ")
    if runbook.get('tags'):
        lines.append(f"**Tags:** {', '.join(runbook['tags'])}  ")
    lines.append(f"**Created:** {runbook.get('created_at', 'N/A')}  ")
    lines.append(f"**Updated:** {runbook.get('updated_at', 'N/A')}  ")
    lines.append("")

    context = runbook.get('context', {})
    if context:
        lines.append("## Context\n")
        if context.get('source_program'):
            lines.append(f"- **Source Program:** {context['source_program']}")
        if context.get('target_project'):
            lines.append(f"- **Target Project:** {context['target_project']}")
        lines.append("")

    steps = runbook.get('steps', [])
    if steps:
        lines.append("## Steps\n")
        for step in steps:
            lines.append(f"### Step {step['n']}: {step['action']}\n")
            lines.append(f"**Actor:** {step['actor']}  ")
            lines.append(f"**Expected:** {step['expected']}  ")
            if step.get('details'):
                lines.append(f"\n{step['details']}\n")
            if step.get('variants'):
                lines.append("\n**Variants:**")
                for variant in step['variants']:
                    lines.append(f"- {variant}")
                lines.append("")

    links = runbook.get('links', {})
    if any(links.get(k) for k in ['workflows', 'issues', 'tasks']):
        lines.append("## Links\n")
        if links.get('workflows'):
            lines.append(f"**Workflows:** {', '.join(links['workflows'])}  ")
        if links.get('issues'):
            lines.append(f"**Issues:** {', '.join(links['issues'])}  ")
        if links.get('tasks'):
            lines.append(f"**Tasks:** {', '.join(links['tasks'])}  ")

    return '\n'.join(lines)


def _export_runbook_puml(runbook: Dict[str, Any]) -> str:
    """Export runbook to PlantUML format (simple activity diagram)."""
    lines = []
    lines.append("@startuml")
    lines.append(f"title Runbook: {runbook['title']}")
    lines.append("")
    lines.append("start")

    steps = runbook.get('steps', [])
    for step in steps:
        lines.append(f":{step['action']}|{step['actor']};")
        lines.append(f"note right: {step['expected']}")
        if step.get('variants'):
            lines.append("if (variant?) then (yes)")
            for variant in step['variants']:
                lines.append(f"  :{variant};")
            lines.append("endif")

    lines.append("stop")
    lines.append("@enduml")

    return '\n'.join(lines)


def handle_runbook_render(args: argparse.Namespace) -> None:
    """Handle the runbook render command."""
    import subprocess

    # First export to PUML
    runbook = _load_runbook(args.id)
    if not runbook:
        print(f"Error: Runbook '{args.id}' not found.")
        return

    _ensure_runbook_storage()
    puml_path = _get_runbook_storage_path() / "exports" / f"{args.id}.puml"
    puml_content = _export_runbook_puml(runbook)

    puml_path.parent.mkdir(parents=True, exist_ok=True)
    with open(puml_path, 'w') as f:
        f.write(puml_content)

    # Determine SVG output path
    if hasattr(args, 'out') and args.out:
        svg_path = Path(args.out)
    else:
        svg_path = _get_runbook_storage_path() / "exports" / f"{args.id}.svg"

    # Render with PlantUML
    try:
        result = subprocess.run(
            ['/usr/bin/plantuml', '-tsvg', str(puml_path)],
            capture_output=True,
            text=True,
            check=True
        )
        print(f"Rendered runbook {args.id} to {svg_path}")
        print(f"PUML source: {puml_path}")
    except subprocess.CalledProcessError as e:
        print(f"Error rendering PlantUML: {e}")
        print(f"PUML source saved at: {puml_path}")
    except FileNotFoundError:
        print("Error: /usr/bin/plantuml not found. Install PlantUML to use this feature.")
        print(f"PUML source saved at: {puml_path}")


def handle_runbook_discuss(args: argparse.Namespace) -> None:
    """Handle the runbook discuss command (placeholder)."""
    runbook = _load_runbook(args.id)
    if not runbook:
        print(f"Error: Runbook '{args.id}' not found.")
        return

    print(f"AI Discuss for runbook: {runbook['title']}")
    print("\n[PLACEHOLDER: AI Discussion Integration]")
    print("\nThis command will integrate with the existing discuss mechanism.")
    print("It will analyze the runbook and suggest CLI commands for:")
    print("  - Adding/refining steps")
    print("  - Converting to workflow graphs")
    print("  - Linking to issues/tasks")
    print("\nSuggested CLI commands:")
    print(f"  maestro runbook step-add {args.id} --actor user --action \"...\" --expected \"...\"")
    print(f"  maestro runbook export {args.id} --format puml")
    print(f"  maestro workflow create --from-runbook {args.id}")


def handle_runbook_archive(args: argparse.Namespace) -> None:
    """Handle the runbook archive command."""
    from maestro.archive.runbook_archive import (
        ArchiveError,
        archive_runbook_json,
        archive_runbook_markdown,
    )

    id_or_path = args.id_or_path
    reason = getattr(args, 'reason', None)

    # Determine if this is a path (markdown) or ID (JSON)
    path_obj = Path(id_or_path)

    try:
        if path_obj.exists() and path_obj.is_file():
            # Archive markdown file
            entry = archive_runbook_markdown(path_obj, reason=reason)
            print(f"Archived markdown runbook: {path_obj}")
            print(f"Archive ID: {entry.archive_id}")
            print(f"Archived to: {entry.archived_path}")
        else:
            # Archive JSON runbook by ID
            entry = archive_runbook_json(id_or_path, reason=reason)
            print(f"Archived JSON runbook: {id_or_path}")
            print(f"Archive ID: {entry.archive_id}")
            print(f"Archived to: {entry.archived_path}")

        if reason:
            print(f"Reason: {reason}")

    except ArchiveError as e:
        print(f"Error: {e}")
        return


from maestro.ai.engine_selector import select_engine_for_role, get_worker_engine, get_planner_engine
from maestro.ai.types import AiEngineName

def handle_runbook_resolve(args: argparse.Namespace) -> None:
    """Handle the runbook resolve command."""
    import sys
    import hashlib
    from typing import Any, Dict, List, Callable, Optional

    # Check if stdin is a TTY when using -e flag
    if args.eval:
        if sys.stdin.isatty():
            print("Error: -e flag requires input from stdin, not terminal.", file=sys.stderr)
            print("Usage: echo 'your text' | maestro runbook resolve -e", file=sys.stderr)
            return
        # Read from stdin
        freeform_input = sys.stdin.read()
    else:
        # Check if text argument is provided
        if not args.text:
            print("Error: Text argument is required when -e flag is not set.", file=sys.stderr)
            print("Usage: maestro runbook resolve 'your text here'", file=sys.stderr)
            return
        freeform_input = args.text

    # Determine if we should use evidence collection
    use_evidence = not getattr(args, 'no_evidence', False)

    # Collect evidence if requested
    evidence = None
    evidence_pack = None

    if use_evidence:
        from pathlib import Path
        from maestro.repo.evidence_pack import (
            EvidenceCollector,
            load_evidence_pack
        )
        from maestro.repo.profile import load_profile

        repo_root = Path.cwd()

        # Check if --evidence-pack <ID> was provided
        if getattr(args, 'evidence_pack', None):
            # Load existing pack
            storage_dir = repo_root / "docs" / "maestro" / "evidence_packs"
            evidence_pack = load_evidence_pack(args.evidence_pack, storage_dir)

            if not evidence_pack:
                print(f"Error: Evidence pack not found: {args.evidence_pack}", file=sys.stderr)
                print(f"Storage dir: {storage_dir}", file=sys.stderr)
                print("Run 'maestro repo evidence pack --save' to create one", file=sys.stderr)
                sys.exit(1)

            if args.verbose:
                print(f"Using evidence pack: {evidence_pack.meta.pack_id}")
                print(f"  Evidence count: {evidence_pack.meta.evidence_count}")
                print(f"  Total bytes: {evidence_pack.meta.total_bytes:,}")
        else:
            # Generate pack on the fly
            profile = load_profile(repo_root)

            # Get budgets from profile or use defaults
            if profile and profile.evidence_rules:
                max_files = profile.evidence_rules.max_files
                max_bytes = profile.evidence_rules.max_bytes
                max_help_calls = profile.evidence_rules.max_help_calls
                timeout_seconds = profile.evidence_rules.timeout_seconds
                prefer_dirs = profile.evidence_rules.prefer_dirs
                exclude_patterns = profile.evidence_rules.exclude_patterns
            else:
                max_files = 60
                max_bytes = 250000
                max_help_calls = 6
                timeout_seconds = 5
                prefer_dirs = []
                exclude_patterns = []

            # Create collector
            collector = EvidenceCollector(
                repo_root=repo_root,
                max_files=max_files,
                max_bytes=max_bytes,
                max_help_calls=max_help_calls,
                timeout_seconds=timeout_seconds,
                prefer_dirs=prefer_dirs,
                exclude_patterns=exclude_patterns
            )

            # Get CLI candidates from profile
            cli_candidates = None
            if profile:
                cli_candidates = profile.cli_help_candidates

            # Collect evidence
            evidence_pack = collector.collect_all(cli_candidates=cli_candidates)

            if args.verbose:
                print(f"Generated evidence pack: {evidence_pack.meta.pack_id}")
                print(f"  Evidence count: {evidence_pack.meta.evidence_count}")
                print(f"  Total bytes: {evidence_pack.meta.total_bytes:,}")

        # Show pack summary in very verbose mode
        if getattr(args, 'very_verbose', False):
            print("\n=== EVIDENCE PACK SUMMARY ===")
            print(f"Pack ID: {evidence_pack.meta.pack_id}")
            print(f"Created: {evidence_pack.meta.created_at}")
            print(f"Items: {evidence_pack.meta.evidence_count}")

            kind_counts = {}
            for item in evidence_pack.items:
                kind_counts[item.kind] = kind_counts.get(item.kind, 0) + 1

            print("By kind:")
            for kind, count in sorted(kind_counts.items()):
                print(f"  {kind}: {count}")

            if evidence_pack.meta.truncated_items:
                print(f"Truncated: {len(evidence_pack.meta.truncated_items)} items")
            if evidence_pack.meta.skipped_items:
                print(f"Skipped (budget): {len(evidence_pack.meta.skipped_items)} items")
            print()

        # Convert evidence pack to old RunbookEvidence format for backward compatibility
        commands_docs = []
        help_text = None
        help_bin_path = None
        warnings = list(evidence_pack.meta.skipped_items) if evidence_pack.meta.skipped_items else []

        for item in evidence_pack.items:
            if item.kind == "docs" and "commands" in item.source.lower():
                # Extract title and summary from docs content
                lines = item.content.split('\n')
                title = lines[0].strip('#').strip() if lines else item.source
                summary = '\n'.join(lines[1:10]) if len(lines) > 1 else ""
                commands_docs.append({
                    'filename': Path(item.source).name,
                    'title': title,
                    'summary': summary
                })
            elif item.kind == "command" and "--help" in item.source:
                # Use first help output as help_text
                if help_text is None:
                    help_text = item.content
                    help_bin_path = item.source.replace(" --help", "")

        evidence = RunbookEvidence(
            commands_docs=commands_docs,
            help_text=help_text,
            help_bin_path=help_bin_path,
            warnings=warnings
        )

    # Treat -vv as implying -v
    effective_verbose = args.verbose or getattr(args, 'very_verbose', False)

    # Determine which generator to use
    # Handle backward compatibility: if engine is 'evidence', use evidence-only
    if getattr(args, 'evidence_only', False) or (hasattr(args, 'engine') and args.engine == 'evidence'):
        # Use evidence-only generator if --evidence-only flag is set or engine is 'evidence'
        generator = EvidenceOnlyGenerator()
        if effective_verbose:
            prompt_hash = hashlib.sha256(freeform_input.encode()).hexdigest()[:8]
            print(f"Prompt hash: {prompt_hash}")
            print(f"Engine: [EVIDENCE_ONLY - deterministic compilation]")
            print(f"Input: {freeform_input[:100]}{'...' if len(freeform_input) > 100 else ''}")
    else:
        # Use AI engine by default
        try:
            # Select an appropriate engine based on the role
            # For runbook generation, we'll use a worker engine
            # If args.engine is specified and not 'evidence', use it as preferred engine
            preferred_order = None
            if hasattr(args, 'engine') and args.engine and args.engine != 'evidence':
                preferred_order = [args.engine]
            engine = select_engine_for_role('worker', preferred_order=preferred_order)

            if effective_verbose:
                prompt_hash = hashlib.sha256(freeform_input.encode()).hexdigest()[:8]
                print(f"Prompt hash: {prompt_hash}")
                print(f"Engine: {engine.name}")
                print(f"Input: {freeform_input[:100]}{'...' if len(freeform_input) > 100 else ''}")

            # Create an AI-based generator
            actionable = getattr(args, 'actionable', False)
            generator = AIRunbookGenerator(engine, verbose=effective_verbose, actionable=actionable)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            print("No AI engine available. Configure an engine or use --evidence-only flag.", file=sys.stderr)
            sys.exit(1)

    # Generate the runbook using the appropriate generator
    if evidence is not None:
        runbook_data = generator.generate(evidence, freeform_input)

        # Print prompt and AI output if very verbose (bounded to 2000 chars)
        if getattr(args, 'very_verbose', False) and isinstance(generator, AIRunbookGenerator):
            print("\n=== AI PROMPT (first 2000 chars) ===")
            prompt = generator.last_prompt or ""
            print(prompt[:2000])
            if len(prompt) > 2000:
                print(f"\n... (truncated {len(prompt) - 2000} chars)")

            print("\n=== AI RESPONSE (first 2000 chars) ===")
            response = generator.last_response or ""
            formatted_output = format_ai_output_for_display(response[:2000])
            print(formatted_output)
            if len(response) > 2000:
                print(f"\n... (truncated {len(response) - 2000} chars)")
            print()
    else:
        # Fallback to basic generation if no evidence
        title = freeform_input[:100] if freeform_input else "Runbook from freeform text"
        runbook_id = generate_runbook_id(title)
        runbook_data = {
            'id': runbook_id,
            'title': title,
            'goal': freeform_input[:500],
            'steps': [
                {
                    'n': 1,
                    'actor': 'dev',
                    'action': 'Implement steps based on requirements',
                    'expected': 'Requirements fulfilled'
                }
            ],
            'tags': ['generated'],
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }

    if runbook_data is None:
        print("Error: Failed to generate runbook from input.", file=sys.stderr)
        return

    # Apply custom name if provided
    if getattr(args, 'name', None):
        runbook_data['title'] = args.name
        # Regenerate ID based on the custom name
        runbook_data['id'] = generate_runbook_id(args.name)

    # Validate the runbook data (schema)
    validation_errors = validate_runbook_schema(runbook_data)
    if validation_errors:
        # FALLBACK: Generate WorkGraph instead
        if effective_verbose:
            print("Runbook schema validation failed. Falling back to WorkGraph generation...")
            print(f"Schema errors: {validation_errors[:3]}")  # Show first 3 errors

        try:
            from maestro.builders.workgraph_generator import WorkGraphGenerator
            from maestro.archive.workgraph_storage import save_workgraph
            from maestro.config.paths import get_workgraph_dir
            from maestro.repo.discovery import discover_repo, DiscoveryBudget
            from pathlib import Path

            # Collect repo evidence for WorkGraph (same as plan decompose)
            repo_root = Path.cwd()
            budget = DiscoveryBudget()
            discovery = discover_repo(repo_root, budget)

            if effective_verbose:
                print(f"Collected {len(discovery.evidence)} evidence items for WorkGraph")

            # Use same engine as runbook generation
            if not isinstance(generator, AIRunbookGenerator):
                # If using EvidenceOnlyGenerator, we can't generate WorkGraph
                print("Error: Runbook validation failed and WorkGraph fallback requires AI engine.", file=sys.stderr)
                print("Use --engine option to specify an AI engine.", file=sys.stderr)
                return

            wg_generator = WorkGraphGenerator(
                engine=generator.engine,
                verbose=effective_verbose
            )

            workgraph = wg_generator.generate(
                freeform_request=freeform_input,
                discovery=discovery,
                domain="runbook",
                profile=getattr(args, 'profile', 'default')
            )

            # Very verbose: show AI prompt and response (bounded to 2000 chars)
            if getattr(args, 'very_verbose', False):
                print("\n=== AI PROMPT (first 2000 chars) ===")
                prompt = wg_generator.last_prompt or ""
                print(prompt[:2000])
                if len(prompt) > 2000:
                    print(f"\n... (truncated {len(prompt) - 2000} chars)")

                print("\n=== AI RESPONSE (first 2000 chars) ===")
                response = wg_generator.last_response or ""
                print(response[:2000])
                if len(response) > 2000:
                    print(f"\n... (truncated {len(response) - 2000} chars)")
                print()

            # Save WorkGraph
            wg_dir = get_workgraph_dir()
            wg_path = wg_dir / f"{workgraph.id}.json"
            save_workgraph(workgraph, wg_path)

            print("\nRunbook too big/ambiguous → created WorkGraph instead")
            print(f"WorkGraph ID: {workgraph.id}")
            print(f"Domain: {workgraph.domain}")
            print(f"Phases: {len(workgraph.phases)}")
            total_tasks = sum(len(p.tasks) for p in workgraph.phases)
            print(f"Tasks: {total_tasks}")
            print(f"\nNext step: Run the following command to materialize the plan:")
            print(f"  maestro plan enact {workgraph.id}")
            return

        except Exception as wg_error:
            print(f"Error: Both runbook and WorkGraph generation failed.", file=sys.stderr)
            print(f"  Runbook errors: {validation_errors[:2]}", file=sys.stderr)
            print(f"  WorkGraph error: {wg_error}", file=sys.stderr)
            if effective_verbose:
                import traceback
                traceback.print_exc()
            return

    # Schema validation passed
    if effective_verbose:
        print(f"Schema validation: passed")

    # Actionability validation (only if --actionable flag is set)
    if getattr(args, 'actionable', False):
        actionability_errors = validate_runbook_actionability(runbook_data)

        if actionability_errors:
            # FALLBACK: Generate WorkGraph instead
            if effective_verbose:
                print("Runbook actionability validation failed. Falling back to WorkGraph generation...")
                print(f"Actionability errors ({len(actionability_errors)}):")
                for error in actionability_errors[:5]:  # Show first 5 errors
                    print(f"  - {error}")

            # Very verbose: show actionability failure reasons (bounded)
            if getattr(args, 'very_verbose', False):
                print("\n=== ACTIONABILITY VALIDATION FAILURES ===")
                for error in actionability_errors:
                    print(f"  {error}")
                print()

            try:
                from maestro.builders.workgraph_generator import WorkGraphGenerator
                from maestro.archive.workgraph_storage import save_workgraph
                from maestro.config.paths import get_workgraph_dir
                from maestro.repo.discovery import discover_repo, DiscoveryBudget
                from pathlib import Path

                # Collect repo evidence for WorkGraph (same as plan decompose)
                repo_root = Path.cwd()
                budget = DiscoveryBudget()
                discovery = discover_repo(repo_root, budget)

                if effective_verbose:
                    print(f"Collected {len(discovery.evidence)} evidence items for WorkGraph")

                # Use same engine as runbook generation
                if not isinstance(generator, AIRunbookGenerator):
                    # If using EvidenceOnlyGenerator, we can't generate WorkGraph
                    print("Error: Runbook actionability failed and WorkGraph fallback requires AI engine.", file=sys.stderr)
                    print("Use --engine option to specify an AI engine.", file=sys.stderr)
                    return

                wg_generator = WorkGraphGenerator(
                    engine=generator.engine,
                    verbose=effective_verbose
                )

                workgraph = wg_generator.generate(
                    freeform_request=freeform_input,
                    discovery=discovery,
                    domain="runbook",
                    profile=getattr(args, 'profile', 'default')
                )

                # Very verbose: show AI prompt and response (bounded to 2000 chars)
                if getattr(args, 'very_verbose', False):
                    print("\n=== AI PROMPT (first 2000 chars) ===")
                    prompt = wg_generator.last_prompt or ""
                    print(prompt[:2000])
                    if len(prompt) > 2000:
                        print(f"\n... (truncated {len(prompt) - 2000} chars)")

                    print("\n=== AI RESPONSE (first 2000 chars) ===")
                    response = wg_generator.last_response or ""
                    print(response[:2000])
                    if len(response) > 2000:
                        print(f"\n... (truncated {len(response) - 2000} chars)")
                    print()

                # Save WorkGraph
                wg_dir = get_workgraph_dir()
                wg_path = wg_dir / f"{workgraph.id}.json"
                save_workgraph(workgraph, wg_path)

                print("\nRunbook not actionable → created WorkGraph instead")
                print(f"WorkGraph ID: {workgraph.id}")
                print(f"Domain: {workgraph.domain}")
                print(f"Phases: {len(workgraph.phases)}")
                total_tasks = sum(len(p.tasks) for p in workgraph.phases)
                print(f"Tasks: {total_tasks}")
                print(f"\nNext step: Run the following command to materialize the plan:")
                print(f"  maestro plan enact {workgraph.id}")
                return

            except Exception as wg_error:
                print(f"Error: Both runbook validation and WorkGraph generation failed.", file=sys.stderr)
                print(f"  Actionability errors: {actionability_errors[:2]}", file=sys.stderr)
                print(f"  WorkGraph error: {wg_error}", file=sys.stderr)
                if effective_verbose:
                    import traceback
                    traceback.print_exc()
                return

        # Actionability validation passed
        if effective_verbose:
            print(f"Actionability validation: passed")

    # Check for dry run
    if getattr(args, 'dry_run', False):
        print("DRY RUN: Would create/update runbook with the following data:")
        print(json.dumps(runbook_data, indent=2))
        return

    # Save the runbook
    save_runbook_with_update_semantics(runbook_data)

    print(f"Created/updated runbook: {runbook_data['id']}")
    print(f"  Title: {runbook_data['title']}")


def handle_runbook_restore(args: argparse.Namespace) -> None:
    """Handle the runbook restore command."""
    from maestro.archive.runbook_archive import (
        RestoreError,
        find_archive_entry,
        restore_runbook_json,
        restore_runbook_markdown,
    )

    archive_id = args.archive_id

    try:
        # Find the entry to determine type
        entry = find_archive_entry(archive_id)
        if not entry:
            print(f"Error: Archive not found: {archive_id}")
            return

        # Restore based on type
        if entry.type == "runbook_markdown":
            restored_path = restore_runbook_markdown(archive_id)
            print(f"Restored markdown runbook: {restored_path}")
        elif entry.type == "runbook_json":
            restored_id = restore_runbook_json(archive_id)
            print(f"Restored JSON runbook: {restored_id}")
        else:
            print(f"Error: Unknown archive type: {entry.type}")
            return

        print(f"Restored from: {entry.archived_path}")

    except RestoreError as e:
        print(f"Error: {e}")
        return
