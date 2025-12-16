"""
Conversion Memory Management Module

Handles persistent memory store for preventing context rot, 
hallucination drift, and "AI amnesia" during long conversions.
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import hashlib


class ConversionMemory:
    """Manages the conversion memory store with authoritative decision tracking."""
    
    def __init__(self, base_path: str = ".maestro/convert/memory"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize memory files
        self.decisions_path = self.base_path / "decisions.json"
        self.conventions_path = self.base_path / "conventions.json"
        self.open_issues_path = self.base_path / "open_issues.json"
        self.glossary_path = self.base_path / "glossary.json"
        self.summary_log_path = self.base_path / "summary.log"
        
        # Create files with empty arrays if they don't exist
        self._ensure_file_exists(self.decisions_path, [])
        self._ensure_file_exists(self.conventions_path, [])
        self._ensure_file_exists(self.open_issues_path, [])
        self._ensure_file_exists(self.glossary_path, [])
        self._ensure_file_exists(self.summary_log_path, [])
    
    def _ensure_file_exists(self, path: Path, default_value: Any):
        """Create file with default value if it doesn't exist."""
        if not path.exists():
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(default_value, f, indent=2)
    
    def load_decisions(self) -> List[Dict]:
        """Load all decisions from memory."""
        with open(self.decisions_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_decisions(self, decisions: List[Dict]):
        """Save all decisions to memory."""
        with open(self.decisions_path, 'w', encoding='utf-8') as f:
            json.dump(decisions, f, indent=2)
    
    def get_decision_by_id(self, decision_id: str) -> Optional[Dict]:
        """Get a specific decision by ID."""
        decisions = self.load_decisions()
        for decision in decisions:
            if decision.get('decision_id') == decision_id:
                return decision
        return None
    
    def add_decision(self, category: str, description: str, value: Any, justification: str,
                     created_by: str = "planner", status: str = "active", evidence_refs: Optional[List[str]] = None) -> str:
        """Add a new decision to memory."""
        decisions = self.load_decisions()

        # Generate unique decision ID
        timestamp = datetime.now().isoformat()
        decision_id = f"D-{len(decisions) + 1:03d}"  # Format: D-001, D-002, etc.

        new_decision = {
            "decision_id": decision_id,
            "title": description,  # Adding the title field as requested
            "status": status,
            "created_at": timestamp,
            "created_by": created_by,
            "category": category,
            "description": description,
            "value": value,
            "justification": justification,
            "evidence_refs": evidence_refs or []
        }

        decisions.append(new_decision)
        self.save_decisions(decisions)

        return decision_id
    
    def load_conventions(self) -> List[Dict]:
        """Load all conventions from memory."""
        with open(self.conventions_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_conventions(self, conventions: List[Dict]):
        """Save all conventions to memory."""
        with open(self.conventions_path, 'w', encoding='utf-8') as f:
            json.dump(conventions, f, indent=2)
    
    def get_convention_by_id(self, convention_id: str) -> Optional[Dict]:
        """Get a specific convention by ID."""
        conventions = self.load_conventions()
        for convention in conventions:
            if convention.get('convention_id') == convention_id:
                return convention
        return None
    
    def add_convention(self, category: str, rule: str, applies_to: str) -> str:
        """Add a new convention to memory."""
        conventions = self.load_conventions()
        
        # Generate unique convention ID
        timestamp = datetime.now().isoformat()
        convention_id = f"C-{len(conventions) + 1:03d}"  # Format: C-001, C-002, etc.
        
        new_convention = {
            "convention_id": convention_id,
            "timestamp": timestamp,
            "category": category,
            "rule": rule,
            "applies_to": applies_to
        }
        
        conventions.append(new_convention)
        self.save_conventions(conventions)
        
        return convention_id
    
    def load_open_issues(self) -> List[Dict]:
        """Load all open issues from memory."""
        with open(self.open_issues_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_open_issues(self, issues: List[Dict]):
        """Save all open issues to memory."""
        with open(self.open_issues_path, 'w', encoding='utf-8') as f:
            json.dump(issues, f, indent=2)
    
    def get_issue_by_id(self, issue_id: str) -> Optional[Dict]:
        """Get a specific issue by ID."""
        issues = self.load_open_issues()
        for issue in issues:
            if issue.get('issue_id') == issue_id:
                return issue
        return None
    
    def add_issue(self, severity: str, description: str, related_tasks: List[str], status: str = "open") -> str:
        """Add a new issue to memory."""
        issues = self.load_open_issues()
        
        # Generate unique issue ID
        timestamp = datetime.now().isoformat()
        issue_id = f"I-{len(issues) + 1:03d}"  # Format: I-001, I-002, etc.
        
        new_issue = {
            "issue_id": issue_id,
            "timestamp": timestamp,
            "severity": severity,
            "description": description,
            "status": status,
            "related_tasks": related_tasks
        }
        
        issues.append(new_issue)
        self.save_open_issues(issues)
        
        return issue_id
    
    def update_issue_status(self, issue_id: str, status: str, resolution: Optional[str] = None):
        """Update the status of an existing issue."""
        issues = self.load_open_issues()

        for issue in issues:
            if issue.get('issue_id') == issue_id:
                issue['status'] = status
                if resolution:
                    issue['resolution'] = resolution
                break

        self.save_open_issues(issues)

    def override_decision(self, decision_id: str, new_value: Any, reason: str,
                         created_by: str = "user", evidence_refs: Optional[List[str]] = None) -> Dict[str, str]:
        """
        Override a decision by superseding the old one and creating a new one.

        Args:
            decision_id: ID of the decision to override
            new_value: New value for the decision
            reason: Reason for the override
            created_by: Who created the new decision (user, planner, worker)
            evidence_refs: Optional list of evidence references

        Returns:
            Dict with old_id and new_id of the decision
        """
        decisions = self.load_decisions()

        # Find the decision to override
        target_decision = None
        target_index = -1
        for i, decision in enumerate(decisions):
            if decision.get('decision_id') == decision_id:
                target_decision = decision
                target_index = i
                break

        if not target_decision:
            raise ValueError(f"Decision with ID {decision_id} not found")

        # Mark the old decision as superseded
        old_decision = decisions[target_index]
        old_decision['status'] = 'superseded'

        # Create a new decision with the same category/description but new value and reason
        timestamp = datetime.now().isoformat()

        # Generate new decision ID by incrementing the sequence number
        current_seq = int(decision_id.split('-')[1])
        new_decision_id = f"D-{current_seq + 1:03d}"

        new_decision = {
            "decision_id": new_decision_id,
            "title": old_decision.get('title', old_decision.get('description', '')),
            "status": "active",
            "created_at": timestamp,
            "created_by": created_by,
            "category": old_decision.get('category'),
            "description": old_decision.get('description'),
            "value": new_value,
            "justification": reason,
            "reason": reason,  # Explicitly add reason field
            "evidence_refs": evidence_refs or []
        }

        decisions.append(new_decision)
        self.save_decisions(decisions)

        return {
            "old_id": decision_id,
            "new_id": new_decision_id,
            "old_decision": old_decision,
            "new_decision": new_decision
        }
    
    def load_glossary(self) -> List[Dict]:
        """Load all glossary entries from memory."""
        with open(self.glossary_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_glossary(self, glossary: List[Dict]):
        """Save all glossary entries to memory."""
        with open(self.glossary_path, 'w', encoding='utf-8') as f:
            json.dump(glossary, f, indent=2)
    
    def get_glossary_entry_by_id(self, term_id: str) -> Optional[Dict]:
        """Get a specific glossary entry by ID."""
        glossary = self.load_glossary()
        for term in glossary:
            if term.get('term_id') == term_id:
                return term
        return None
    
    def add_glossary_entry(self, source_term: str, target_term: str, definition: str, usage_context: str) -> str:
        """Add a new glossary entry to memory."""
        glossary = self.load_glossary()
        
        # Generate unique term ID
        timestamp = datetime.now().isoformat()
        term_id = f"G-{len(glossary) + 1:03d}"  # Format: G-001, G-002, etc.
        
        new_entry = {
            "term_id": term_id,
            "timestamp": timestamp,
            "source_term": source_term,
            "target_term": target_term,
            "definition": definition,
            "usage_context": usage_context
        }
        
        glossary.append(new_entry)
        self.save_glossary(glossary)
        
        return term_id
    
    def load_summary_log(self) -> List[Dict]:
        """Load all entries from the summary log."""
        with open(self.summary_log_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_summary_log(self, entries: List[Dict]):
        """Save all entries to the summary log."""
        with open(self.summary_log_path, 'w', encoding='utf-8') as f:
            json.dump(entries, f, indent=2)
    
    def add_summary_entry(self, task_id: str, summary: str) -> str:
        """Add a new summary entry to memory."""
        entries = self.load_summary_log()
        
        # Generate unique entry ID
        timestamp = datetime.now().isoformat()
        entry_id = f"S-{len(entries) + 1:03d}"  # Format: S-001, S-002, etc.
        
        new_entry = {
            "entry_id": entry_id,
            "task_id": task_id,
            "timestamp": timestamp,
            "summary": summary
        }
        
        entries.append(new_entry)
        self.save_summary_log(entries)
        
        return entry_id
    
    def get_applicable_decisions(self, categories: Optional[List[str]] = None) -> List[Dict]:
        """Get decisions that match specific categories, or all if no categories specified."""
        decisions = self.load_decisions()
        if categories:
            return [d for d in decisions if d.get('category') in categories]
        return decisions
    
    def get_applicable_conventions(self, categories: Optional[List[str]] = None) -> List[Dict]:
        """Get conventions that match specific categories, or all if no categories specified."""
        conventions = self.load_conventions()
        if categories:
            return [c for c in conventions if c.get('category') in categories]
        return conventions
    
    def get_active_issues(self) -> List[Dict]:
        """Get issues that are currently open or in progress."""
        issues = self.load_open_issues()
        return [i for i in issues if i.get('status') in ['open', 'investigating']]

    def get_active_decisions(self) -> List[Dict]:
        """Get decisions that are currently active."""
        decisions = self.load_decisions()
        return [d for d in decisions if d.get('status') == 'active']

    def compute_decision_fingerprint(self) -> str:
        """Compute a hash fingerprint of all active decisions."""
        import hashlib
        active_decisions = self.get_active_decisions()

        # Sort decisions by ID to ensure consistent hashing
        active_decisions.sort(key=lambda x: x.get('decision_id', ''))

        # Create a string representation of all active decisions
        decisions_str = json.dumps(active_decisions, sort_keys=True)

        return hashlib.sha256(decisions_str.encode('utf-8')).hexdigest()
    
    def get_glossary_entries_by_source(self, source_terms: List[str]) -> List[Dict]:
        """Get glossary entries that match specific source terms."""
        glossary = self.load_glossary()
        return [g for g in glossary if g.get('source_term') in source_terms]
    
    def check_decision_conflict(self, category: str, value: Any) -> Optional[Dict]:
        """Check if a new value conflicts with an existing decision of the same category."""
        decisions = self.load_decisions()
        for decision in decisions:
            if decision.get('category') == category:
                # For simplicity, assume conflict if decision value differs and is not equal
                if decision.get('value') != value:
                    return decision
        return None

    def check_task_compliance(self, task: Dict) -> List[str]:
        """
        Check if a task complies with existing decisions and conventions.
        Returns a list of violations if any.
        """
        violations = []

        # Check for decision conflicts
        # Example: if task specifies a different engine than decided
        if 'engine' in task:
            decisions = self.load_decisions()
            for decision in decisions:
                if decision.get('category') == 'engine_choice' and decision.get('value') != task.get('engine'):
                    violations.append(
                        f"Task {task.get('task_id')} engine '{task.get('engine')}' "
                        f"contradicts decision {decision.get('decision_id')}: "
                        f"should be '{decision.get('value')}'"
                    )

        # Example: check language target if specified in decision
        if 'target_files' in task and len(task.get('target_files', [])) > 0:
            # Infer target language from file extensions and check against decisions
            decisions = self.load_decisions()
            for decision in decisions:
                if decision.get('category') == 'language_target':
                    target_lang = decision.get('value', '').lower()
                    for target_file in task.get('target_files', []):
                        file_ext = Path(target_file).suffix.lower()
                        lang_ext_map = {
                            'python': ['.py'],
                            'javascript': ['.js', '.jsx'],
                            'typescript': ['.ts', '.tsx'],
                            'java': ['.java'],
                            'cpp': ['.cpp', '.cxx', '.cc', '.c++'],
                            'csharp': ['.cs'],
                            'go': ['.go'],
                            'rust': ['.rs'],
                            'ruby': ['.rb'],
                            'php': ['.php'],
                        }

                        expected_extensions = lang_ext_map.get(target_lang, [])
                        if file_ext not in expected_extensions and expected_extensions:
                            violations.append(
                                f"Task {task.get('task_id')} target file '{target_file}' "
                                f"has extension '{file_ext}' which doesn't match decided language '{target_lang}'"
                            )

        # Check naming conventions (if any specific to files)
        conventions = self.load_conventions()
        for convention in conventions:
            if convention.get('category') == 'naming' and 'rule' in convention:
                rule = convention.get('rule', '').lower()
                applies_to = convention.get('applies_to', '').lower()

                # Example: check if target files follow naming conventions
                if 'target_files' in task:
                    for target_file in task.get('target_files', []):
                        # Simple check - could be more sophisticated
                        if 'camelcase' in rule and applies_to in target_file.lower():
                            if '_' in Path(target_file).name and not target_file.endswith('.snake_case'):
                                violations.append(
                                    f"Task {task.get('task_id')} target file '{target_file}' "
                                    f"violates naming convention: {convention.get('rule')} "
                                    f"(decision_id: {convention.get('convention_id')})"
                                )

        return violations
    
    def get_memory_usage_info(self) -> Dict:
        """Get information about memory usage."""
        def get_file_size(path: Path) -> int:
            if path.exists():
                return path.stat().st_size
            return 0
        
        return {
            "decisions_count": len(self.load_decisions()),
            "conventions_count": len(self.load_conventions()),
            "open_issues_count": len(self.load_open_issues()),
            "glossary_count": len(self.load_glossary()),
            "summary_log_count": len(self.load_summary_log()),
            "decisions_size": get_file_size(self.decisions_path),
            "conventions_size": get_file_size(self.conventions_path),
            "open_issues_size": get_file_size(self.open_issues_path),
            "glossary_size": get_file_size(self.glossary_path),
            "summary_log_size": get_file_size(self.summary_log_path)
        }


class TaskSummary:
    """Represents a structured summary of a completed task."""
    
    def __init__(self, task_id: str, source_files: List[str], target_files: List[str]):
        self.task_id = task_id
        self.source_files = source_files
        self.target_files = target_files
        self.timestamp = datetime.now().isoformat()
        self.write_policy = None
        self.merge_strategy = None
        self.semantic_decisions_taken = []
        self.warnings = []
        self.errors = []
        self.hashes_before = {}
        self.hashes_after = {}
        self.diff_references = []
    
    def add_policy_info(self, write_policy: str, merge_strategy: Optional[str] = None):
        """Add policy information to the summary."""
        self.write_policy = write_policy
        if merge_strategy:
            self.merge_strategy = merge_strategy
    
    def add_semantic_decision(self, decision: str):
        """Add a semantic decision taken during the task."""
        self.semantic_decisions_taken.append(decision)
    
    def add_warning(self, warning: str):
        """Add a warning to the summary."""
        self.warnings.append(warning)
    
    def add_error(self, error: str):
        """Add an error to the summary."""
        self.errors.append(error)
    
    def set_hashes(self, before: Dict[str, str], after: Dict[str, str]):
        """Set hash information for files before and after the task."""
        self.hashes_before = before
        self.hashes_after = after
    
    def add_diff_reference(self, diff_ref: str):
        """Add a reference to a diff related to this task."""
        self.diff_references.append(diff_ref)
    
    def to_dict(self) -> Dict:
        """Convert the summary to a dictionary for storage."""
        return {
            "task_id": self.task_id,
            "source_files": self.source_files,
            "target_files": self.target_files,
            "timestamp": self.timestamp,
            "write_policy": self.write_policy,
            "merge_strategy": self.merge_strategy,
            "semantic_decisions_taken": self.semantic_decisions_taken,
            "warnings": self.warnings,
            "errors": self.errors,
            "hashes_before": self.hashes_before,
            "hashes_after": self.hashes_after,
            "diff_references": self.diff_references
        }
    
    def save_to_file(self, base_path: str = ".maestro/convert/summaries"):
        """Save the structured summary to a JSON file."""
        summary_path = Path(base_path)
        summary_path.mkdir(parents=True, exist_ok=True)
        
        filename = f"task_{self.task_id.replace(':', '_')}.json"
        filepath = summary_path / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2)
        
        return str(filepath)


def compute_file_hash(filepath: str) -> str:
    """Compute SHA-256 hash of a file."""
    if not os.path.exists(filepath):
        return ""
    
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        # Read file in chunks to handle large files
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()