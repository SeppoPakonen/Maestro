"""
Semantic Integrity & Loss Detection Module

Implements the semantic integrity layer that detects meaning loss during conversion.
Follows the contract specified in Task 11.
"""

import json
import os
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from maestro.convert.conversion_memory import ConversionMemory


class SemanticIntegrityChecker:
    """Main class for semantic integrity checking and risk detection."""

    def __init__(self, base_path: str = ".maestro/convert/semantics"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # File paths for semantic tracking
        self.summary_path = self.base_path / "summary.json"
        self.open_issues_path = self.base_path / "open_issues.json"
        
        # Initialize summary file
        if not self.summary_path.exists():
            self._init_summary_file()
        
        # Initialize open issues file
        if not self.open_issues_path.exists():
            with open(self.open_issues_path, 'w', encoding='utf-8') as f:
                json.dump([], f, indent=2)

    def _init_summary_file(self):
        """Initialize the semantic summary file with default values."""
        summary = {
            "total_files_checked": 0,
            "equivalence_counts": {
                "high": 0,
                "medium": 0,
                "low": 0,
                "unknown": 0
            },
            "cumulative_risk_flags": {
                "control_flow": 0,
                "memory": 0,
                "concurrency": 0,
                "io": 0,
                "lifetime": 0
            },
            "unresolved_semantic_warnings": 0,
            "last_updated": datetime.now().isoformat()
        }
        
        with open(self.summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)

    def compute_source_snapshot_hash(self, source_files: List[str], source_repo_path: str) -> str:
        """Compute a hash of the source files content for semantic analysis."""
        content_digest = ""
        
        for source_file in source_files:
            source_path = os.path.join(source_repo_path, source_file)
            if os.path.exists(source_path):
                with open(source_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    content_digest += hashlib.sha256(content.encode('utf-8')).hexdigest()
        
        return hashlib.sha256(content_digest.encode('utf-8')).hexdigest()

    def run_semantic_check(self, task: Dict, source_repo_path: str, target_repo_path: str) -> Dict:
        """
        Run semantic integrity check for a completed task.
        
        Returns JSON with semantic equivalence analysis as specified in Task 11.
        """
        task_id = task['task_id']
        
        # Get conversion summary from the task
        conversion_summary = task.get('acceptance_criteria', 'No summary available')
        
        # Compute source snapshot hash
        source_snapshot_hash = self.compute_source_snapshot_hash(
            task.get('source_files', []), 
            source_repo_path
        )
        
        # Get target file content
        target_content = ""
        for target_file in task.get('target_files', []):
            target_path = os.path.join(target_repo_path, target_file)
            if os.path.exists(target_path):
                with open(target_path, 'r', encoding='utf-8', errors='ignore') as f:
                    target_content += f.read() + "\n"
        
        # Get active decisions and glossary from conversion memory
        memory = ConversionMemory()
        active_decisions = memory.get_active_decisions()
        glossary = memory.load_glossary()
        
        # Analyze semantic equivalence using AI (mock implementation here)
        result = self._analyze_semantic_equivalence(
            source_snapshot_hash,
            target_content,
            conversion_summary,
            active_decisions,
            glossary
        )
        
        # Save the semantic check result
        self._save_semantic_check_result(task_id, result)
        
        # Update summary
        self._update_summary(result)
        
        return result

    def _analyze_semantic_equivalence(
        self, 
        source_snapshot_hash: str, 
        target_content: str, 
        conversion_summary: str, 
        active_decisions: List[Dict], 
        glossary: List[Dict]
    ) -> Dict:
        """
        Analyze semantic equivalence between source and target.
        
        This is a sophisticated method that would normally call an AI model.
        For now, it implements heuristic-based analysis with configurable thresholds.
        """
        # This would normally be an AI call, but we'll implement a heuristic version
        # that looks for patterns indicating semantic changes
        
        # Analyze target content for potential semantic risks
        risk_flags = []
        preserved_concepts = []
        changed_concepts = []
        lost_concepts = []
        assumptions = []
        
        # Check for control flow risk
        control_flow_indicators = ['if', 'else', 'while', 'for', 'switch', 'try', 'catch', 'finally']
        has_control_flow = any(indicator in target_content.lower() for indicator in control_flow_indicators)
        if has_control_flow:
            risk_flags.append("control_flow")
        
        # Check for memory management patterns
        memory_indicators = ['malloc', 'free', 'new', 'delete', 'dispose', 'gc', 'memory', 'ptr', 'reference', 'pointer']
        has_memory = any(indicator in target_content.lower() for indicator in memory_indicators)
        if has_memory:
            risk_flags.append("memory")
        
        # Check for concurrency patterns
        concurrency_indicators = ['thread', 'mutex', 'lock', 'sync', 'async', 'parallel', 'concurrent', 'race']
        has_concurrency = any(indicator in target_content.lower() for indicator in concurrency_indicators)
        if has_concurrency:
            risk_flags.append("concurrency")
        
        # Check for I/O patterns
        io_indicators = ['read', 'write', 'file', 'network', 'socket', 'stream', 'db', 'database', 'connection']
        has_io = any(indicator in target_content.lower() for indicator in io_indicators)
        if has_io:
            risk_flags.append("io")
        
        # Check for lifetime management
        lifetime_indicators = ['lifetime', 'scope', 'destructor', 'finalizer', 'RAII', 'garbage', 'dispose', 'cleanup']
        has_lifetime = any(indicator in target_content.lower() for indicator in lifetime_indicators)
        if has_lifetime:
            risk_flags.append("lifetime")
        
        # Simulate AI analysis of semantic preservation
        # In a real implementation, this would be done by an AI model
        semantic_equivalence = "unknown"
        confidence = 0.0
        
        # Determine equivalence based on various factors
        if len(target_content.strip()) == 0:
            semantic_equivalence = "low"
            confidence = 0.9
            lost_concepts.append("all_source_content")
            changed_concepts.append("content_existence")
            assumptions.append("Target file is empty despite conversion attempt")
        else:
            # Heuristic: if target content is very different from source summary, medium risk
            if len(target_content) < len(conversion_summary) * 0.1:
                semantic_equivalence = "medium"
                confidence = 0.7
                assumptions.append("Target content is significantly shorter than expected")
            else:
                # Heuristic: check if source summary keywords appear in target
                summary_keywords = conversion_summary.lower().split()
                if len(summary_keywords) > 0:
                    keyword_matches = sum(1 for kw in summary_keywords[:10] if kw.lower() in target_content.lower())
                    match_ratio = keyword_matches / min(len(summary_keywords), 10)
                    
                    if match_ratio > 0.7:
                        semantic_equivalence = "high"
                        confidence = 0.8
                        preserved_concepts.append("core_functionality")
                    elif match_ratio > 0.3:
                        semantic_equivalence = "medium"
                        confidence = 0.6
                        changed_concepts.append("details_implementation")
                    else:
                        semantic_equivalence = "low"
                        confidence = 0.5
                        lost_concepts.append("functionality_context")
        
        # Add glossary checks
        for entry in glossary:
            source_term = entry.get('source_term', '')
            target_term = entry.get('target_term', '')
            if source_term.lower() in conversion_summary.lower() and target_term.lower() not in target_content.lower():
                lost_concepts.append(f"glossary_term_{source_term}")
                assumptions.append(f"Term mapping '{source_term}' -> '{target_term}' not applied")
        
        # Check if any risk flags are present
        requires_human_review = False
        if semantic_equivalence == "low" or len(risk_flags) > 0:
            requires_human_review = True
        elif semantic_equivalence == "medium" and confidence < 0.7:
            requires_human_review = True
        
        return {
            "semantic_equivalence": semantic_equivalence,
            "confidence": confidence,
            "preserved_concepts": preserved_concepts,
            "changed_concepts": changed_concepts,
            "lost_concepts": lost_concepts,
            "assumptions": assumptions,
            "risk_flags": risk_flags,
            "requires_human_review": requires_human_review
        }

    def _save_semantic_check_result(self, task_id: str, result: Dict):
        """Save semantic check result to file."""
        result_path = self.base_path / f"task_{task_id.replace(':', '_')}.json"
        
        with open(result_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2)

    def _update_summary(self, result: Dict):
        """Update the semantic summary with the new result."""
        with open(self.summary_path, 'r', encoding='utf-8') as f:
            summary = json.load(f)
        
        # Increment total files checked
        summary["total_files_checked"] += 1
        
        # Update equivalence counts
        equiv_level = result.get("semantic_equivalence", "unknown")
        if equiv_level in summary["equivalence_counts"]:
            summary["equivalence_counts"][equiv_level] += 1
        else:
            summary["equivalence_counts"]["unknown"] += 1
        
        # Update risk flags
        for risk_flag in result.get("risk_flags", []):
            if risk_flag in summary["cumulative_risk_flags"]:
                summary["cumulative_risk_flags"][risk_flag] += 1
        
        # Update unresolved warnings if requires human review
        if result.get("requires_human_review", False):
            summary["unresolved_semantic_warnings"] += 1
        
        # Update timestamp
        summary["last_updated"] = datetime.now().isoformat()
        
        # Save updated summary
        with open(self.summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)

    def get_semantic_check_result(self, task_id: str) -> Optional[Dict]:
        """Get semantic check result for a specific task."""
        result_path = self.base_path / f"task_{task_id.replace(':', '_')}.json"
        
        if result_path.exists():
            with open(result_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        return None

    def get_summary(self) -> Dict:
        """Get the current semantic summary."""
        with open(self.summary_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def requires_human_review(self, result: Dict) -> bool:
        """Check if a semantic result requires human review."""
        return result.get("requires_human_review", False)

    def classify_risk_level(self, result: Dict, accept_semantic_risk: bool = False) -> str:
        """
        Classify the risk level of a semantic check result.

        Returns:
        - "block" if pipeline should be blocked
        - "pause" if pipeline should pause for review
        - "escalate" if requires escalation
        - "continue" if safe to continue
        """
        semantic_equivalence = result.get("semantic_equivalence", "unknown")
        confidence = result.get("confidence", 0.0)
        requires_human_review = result.get("requires_human_review", False)
        risk_flags = result.get("risk_flags", [])

        # Block pipeline if semantic equivalence is low
        if semantic_equivalence == "low":
            return "block"

        # Pause if human review is required and --accept-semantic-risk is not provided
        if requires_human_review and not accept_semantic_risk:
            return "pause"

        # Escalate if there are high-risk flags and low confidence
        threshold = 0.6  # Configurable threshold
        if risk_flags and confidence < threshold:
            return "escalate"

        # Continue if high equivalence and no risks
        if semantic_equivalence == "high" and not risk_flags:
            return "continue"

        # Default: continue for now
        return "continue"

    def check_semantic_drift_thresholds(self, threshold_config: Optional[Dict] = None) -> bool:
        """
        Check if semantic drift has exceeded acceptable thresholds.

        Args:
            threshold_config: Optional dict with custom thresholds.
                             Defaults will be used if not provided.

        Returns:
            True if drift is within acceptable limits, False if exceeded
        """
        if threshold_config is None:
            # Default thresholds
            threshold_config = {
                "max_low_equivalence_ratio": 0.2,  # 20% of files can have low equivalence
                "max_unresolved_warnings": 10,     # Max 10 unresolved warnings
                "max_control_flow_risk_ratio": 0.3,  # Max 30% of files with control flow risk
                "max_memory_risk_ratio": 0.2       # Max 20% of files with memory risk
            }

        summary = self.get_summary()
        total_checked = summary.get("total_files_checked", 0)

        if total_checked == 0:
            return True  # No files checked yet, so drift is acceptable

        # Calculate ratios
        low_count = summary["equivalence_counts"].get("low", 0)
        control_flow_count = summary["cumulative_risk_flags"].get("control_flow", 0)
        memory_count = summary["cumulative_risk_flags"].get("memory", 0)
        unresolved_warnings = summary.get("unresolved_semantic_warnings", 0)

        low_ratio = low_count / total_checked if total_checked > 0 else 0
        control_flow_ratio = control_flow_count / total_checked if total_checked > 0 else 0
        memory_ratio = memory_count / total_checked if total_checked > 0 else 0

        # Check each threshold
        if low_ratio > threshold_config["max_low_equivalence_ratio"]:
            print(f"Semantic drift exceeded: {low_ratio:.2%} low equivalence (max {threshold_config['max_low_equivalence_ratio']:.2%})")
            return False

        if unresolved_warnings > threshold_config["max_unresolved_warnings"]:
            print(f"Semantic drift exceeded: {unresolved_warnings} unresolved warnings (max {threshold_config['max_unresolved_warnings']})")
            return False

        if control_flow_ratio > threshold_config["max_control_flow_risk_ratio"]:
            print(f"Semantic drift exceeded: {control_flow_ratio:.2%} control flow risk (max {threshold_config['max_control_flow_risk_ratio']:.2%})")
            return False

        if memory_ratio > threshold_config["max_memory_risk_ratio"]:
            print(f"Semantic drift exceeded: {memory_ratio:.2%} memory risk (max {threshold_config['max_memory_risk_ratio']:.2%})")
            return False

        return True

    def add_open_issue(self, issue: Dict):
        """Add an open issue to the semantic tracking system."""
        issues = []
        if self.open_issues_path.exists():
            with open(self.open_issues_path, 'r', encoding='utf-8') as f:
                issues = json.load(f)

        issues.append(issue)

        with open(self.open_issues_path, 'w', encoding='utf-8') as f:
            json.dump(issues, f, indent=2)

    def get_open_issues(self) -> List[Dict]:
        """Get all open semantic issues."""
        with open(self.open_issues_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def check_cross_file_consistency(self) -> List[Dict]:
        """
        Check for semantic contradictions across tasks.

        Detects:
        - Same concept mapped differently in different files
        - Glossary entries violated
        - Decisions contradicted implicitly

        Returns a list of inconsistency issues found.
        """
        inconsistencies = []

        # Load all semantic check results
        all_results = {}
        for semantic_file in self.base_path.glob("task_*.json"):
            task_id = semantic_file.stem.replace("task_", "")
            with open(semantic_file, 'r', encoding='utf-8') as f:
                try:
                    result = json.load(f)
                    all_results[task_id] = result
                except json.JSONDecodeError:
                    continue  # Skip malformed files

        if len(all_results) < 2:
            return []  # Need at least 2 results to compare

        # Load conversion memory for decisions and glossary
        memory = ConversionMemory()
        active_decisions = memory.get_active_decisions()
        glossary = memory.load_glossary()

        # Check for concept mapping inconsistencies
        concept_maps = {}
        for task_id, result in all_results.items():
            # Extract concepts mentioned in semantic analysis
            for concept in result.get('preserved_concepts', []):
                if concept not in concept_maps:
                    concept_maps[concept] = []
                concept_maps[concept].append((task_id, 'preserved'))

            for concept in result.get('changed_concepts', []):
                if concept not in concept_maps:
                    concept_maps[concept] = []
                concept_maps[concept].append((task_id, 'changed'))

            for concept in result.get('lost_concepts', []):
                if concept not in concept_maps:
                    concept_maps[concept] = []
                concept_maps[concept].append((task_id, 'lost'))

        # Look for concepts treated differently across tasks
        for concept, mappings in concept_maps.items():
            if len(mappings) > 1:  # Concept appears in multiple tasks
                statuses = [status for _, status in mappings]
                unique_statuses = set(statuses)

                # If the same concept has different treatment, flag as inconsistency
                if len(unique_statuses) > 1:
                    inconsistencies.append({
                        "issue_id": f"semantic_inconsistency_{hashlib.md5(concept.encode()).hexdigest()[:8]}",
                        "type": "concept_mapping_inconsistency",
                        "description": f"Concept '{concept}' treated differently across tasks: {dict([(task_id, status) for task_id, status in mappings])}",
                        "affected_tasks": [task_id for task_id, _ in mappings],
                        "severity": "medium"
                    })

        # Check for glossary violations
        for term in glossary:
            source_term = term.get('source_term', '')
            target_term = term.get('target_term', '')

            # Look for tasks that should have used this glossary term but didn't
            for task_id, result in all_results.items():
                # Check if source term appears in task but target term doesn't
                # This is a simple heuristic - a full implementation would parse actual content
                task_description = result.get('assumptions', [])
                if any(source_term.lower() in str(assumption).lower() for assumption in task_description):
                    # If source term was mentioned in assumptions but target wasn't preserved,
                    # it might indicate a glossary violation
                    inconsistencies.append({
                        "issue_id": f"glossary_violation_{hashlib.md5((source_term+target_term+task_id).encode()).hexdigest()[:8]}",
                        "type": "glossary_violation",
                        "description": f"Glossary term '{source_term}' -> '{target_term}' potentially violated in task {task_id}",
                        "affected_tasks": [task_id],
                        "severity": "high"
                    })

        # Check for decision contradictions
        for decision in active_decisions:
            decision_id = decision.get('decision_id', '')
            decision_value = decision.get('value')
            decision_category = decision.get('category', '')

            # Look for tasks that might contradict this decision
            # This is a simplified check - would need more sophisticated analysis in practice
            for task_id, result in all_results.items():
                # Check if task has conflicting patterns
                if decision_category == 'language_target' and result.get('risk_flags', []):
                    if decision_value.lower() == 'python':
                        # If decision is Python but task has Java-specific risks
                        java_risks = [r for r in result.get('risk_flags', []) if 'java' in r.lower()]
                        if java_risks:
                            inconsistencies.append({
                                "issue_id": f"decision_contradiction_{hashlib.md5((decision_id+task_id).encode()).hexdigest()[:8]}",
                                "type": "decision_contradiction",
                                "description": f"Task {task_id} contradicts decision {decision_id} about language target ({decision_value})",
                                "affected_tasks": [task_id],
                                "severity": "high"
                            })

        return inconsistencies

    def process_cross_file_inconsistencies(self, inconsistencies: List[Dict], block_on_inconsistency: bool = True) -> bool:
        """
        Process cross-file inconsistencies by recording them and optionally blocking.

        Returns True if execution should continue, False if blocked due to inconsistencies.
        """
        if not inconsistencies:
            return True

        # Add inconsistencies to open issues
        for inconsistency in inconsistencies:
            self.add_open_issue(inconsistency)

            # Log the inconsistency
            print(f"Semantic inconsistency detected: {inconsistency['description']}")
            print(f"  Type: {inconsistency['type']}, Severity: {inconsistency['severity']}")
            print(f"  Affected tasks: {inconsistency['affected_tasks']}")

        # If blocking is enabled and any inconsistency is high severity, block
        if block_on_inconsistency:
            high_severity_inconsistencies = [i for i in inconsistencies if i.get('severity', '') == 'high']
            if high_severity_inconsistencies:
                print(f"BLOCKING: {len(high_severity_inconsistencies)} high-severity inconsistencies detected, blocking pipeline")
                return False

        return True