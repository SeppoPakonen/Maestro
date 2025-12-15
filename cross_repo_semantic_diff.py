#!/usr/bin/env python3
"""
Cross-Repo Semantic Diff Module

Implements cross-repo semantic diff with drift escalation checkpoints.
"""

import json
import os
import re
import sys
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict
import argparse
from datetime import datetime

from conversion_memory import ConversionMemory
from semantic_integrity import SemanticIntegrityChecker


class CrossRepoSemanticDiff:
    """Main class for cross-repo semantic diff with drift analysis."""

    def __init__(self, base_path: str = ".maestro/convert/semantics/cross_repo"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

        # Set up output file paths
        self.mapping_index_path = self.base_path / "mapping_index.json"
        self.diff_report_json_path = self.base_path / "diff_report.json"
        self.diff_report_md_path = self.base_path / "diff_report.md"

    def generate_mapping_index(self) -> Dict[str, Any]:
        """
        Generate a deterministic cross-repo mapping index from available conversion artifacts.
        """
        mapping_index = {
            "generated_at": datetime.now().isoformat(),
            "source_repo": self._detect_source_repo(),
            "target_repo": self._detect_target_repo(),
            "file_mapping": {},
            "concept_mapping": [],
            "evidence_refs": [],
            "conversion_stats": {}
        }

        # Load plan.json and extract coverage_map and file policies
        plan_path = Path(".maestro/convert/plan.json")
        if plan_path.exists():
            with open(plan_path, 'r', encoding='utf-8') as f:
                plan = json.load(f)
                
            if "coverage_map" in plan:
                mapping_index["file_mapping"] = plan["coverage_map"]
            
            # Extract file policies if present
            for stage in plan.get("stages", []):
                for task in stage.get("tasks", []):
                    if "file_policy" in task:
                        target_files = task.get("target_files", [])
                        policy = task["file_policy"]
                        for target_file in target_files:
                            if target_file in mapping_index["file_mapping"]:
                                mapping_index["file_mapping"][target_file]["policy"] = policy
                            else:
                                mapping_index["file_mapping"][target_file] = {
                                    "policy": policy,
                                    "source_file": task.get("source_file", "unknown")
                                }

        # Load coverage.json if it exists
        coverage_path = Path(".maestro/convert/coverage.json")
        if coverage_path.exists():
            with open(coverage_path, 'r', encoding='utf-8') as f:
                coverage_data = json.load(f)
                mapping_index["conversion_stats"] = coverage_data

        # Load glossary from conversion memory
        memory = ConversionMemory()
        glossary = memory.load_glossary()
        mapping_index["concept_mapping"] = glossary

        # Include evidence refs from task semantic reports
        semantic_files = list(Path(".maestro/convert/semantics").glob("task_*.json"))
        for sem_file in semantic_files:
            task_id = sem_file.name.replace("task_", "").replace(".json", "")
            mapping_index["evidence_refs"].append({
                "task_id": task_id,
                "report_path": str(sem_file),
                "semantic_analysis_file": str(sem_file)
            })

        # Include evidence refs from summaries
        summary_files = list(Path(".maestro/convert/summaries").glob("task_*.json"))
        for summary_file in summary_files:
            task_id = summary_file.name.replace("task_", "").replace(".json", "")
            mapping_index["evidence_refs"].append({
                "task_id": task_id,
                "report_path": str(summary_file),
                "summary_file": str(summary_file)
            })

        # Save the mapping index
        with open(self.mapping_index_path, 'w', encoding='utf-8') as f:
            json.dump(mapping_index, f, indent=2)

        return mapping_index

    def _detect_source_repo(self) -> Dict[str, str]:
        """Detect source repository information."""
        # Look for source repo info in conversion pipeline files
        pipeline_files = list(Path(".maestro/convert").glob("pipeline_*.json"))
        for pf in pipeline_files:
            try:
                with open(pf, 'r', encoding='utf-8') as f:
                    pipeline = json.load(f)
                    if 'source' in pipeline:
                        return {
                            'path': pipeline['source'],
                            'type': 'git' if os.path.exists(os.path.join(pipeline['source'], '.git')) else 'directory'
                        }
            except:
                continue
        
        return {"path": "unknown", "type": "unknown"}

    def _detect_target_repo(self) -> Dict[str, str]:
        """Detect target repository information."""
        # Look for target repo info in conversion pipeline files
        pipeline_files = list(Path(".maestro/convert").glob("pipeline_*.json"))
        for pf in pipeline_files:
            try:
                with open(pf, 'r', encoding='utf-8') as f:
                    pipeline = json.load(f)
                    if 'target' in pipeline:
                        return {
                            'path': pipeline['target'],
                            'type': 'git' if os.path.exists(os.path.join(pipeline['target'], '.git')) else 'directory'
                        }
            except:
                continue
        
        return {"path": "unknown", "type": "unknown"}

    def run_semantic_diff(self, top_n: int = 20, filter_pattern: Optional[str] = None, 
                         output_format: str = "text", against_baseline: Optional[str] = None) -> Dict[str, Any]:
        """
        Run cross-repo semantic diff analysis.
        """
        # If comparing against baseline, handle that first
        if against_baseline and against_baseline.startswith("baseline:"):
            baseline_id = against_baseline.replace("baseline:", "")
            return self._compare_with_baseline(baseline_id, top_n, filter_pattern, output_format)

        # Load mapping index
        if self.mapping_index_path.exists():
            with open(self.mapping_index_path, 'r', encoding='utf-8') as f:
                mapping_index = json.load(f)
        else:
            # Generate mapping index if it doesn't exist
            mapping_index = self.generate_mapping_index()

        # Load all semantic reports
        semantic_reports = self._load_all_semantic_reports()

        # Load all task summaries
        task_summaries = self._load_all_task_summaries()

        # Compute deterministic heuristics
        heuristics_data = self._compute_deterministic_heuristics(mapping_index, semantic_reports, task_summaries)

        # Calculate file-level equivalence
        file_equivalence = self._calculate_file_equivalence(semantic_reports, heuristics_data)

        # Calculate concept coverage
        concept_coverage = self._calculate_concept_coverage(semantic_reports, mapping_index)

        # Build loss ledger
        loss_ledger = self._build_loss_ledger(semantic_reports)

        # Identify top risk hotspots
        risk_hotspots = self._identify_risk_hotspots(semantic_reports, heuristics_data, top_n)

        # Create diff report
        diff_report = {
            "generated_at": datetime.now().isoformat(),
            "parameters": {
                "top_n": top_n,
                "filter_pattern": filter_pattern,
                "output_format": output_format
            },
            "file_equivalence": file_equivalence,
            "concept_coverage": concept_coverage,
            "loss_ledger": loss_ledger,
            "top_risk_hotspots": risk_hotspots,
            "heuristics_evidence": heuristics_data,
            "mapping_index_ref": str(self.mapping_index_path),
            "drift_threshold_analysis": self._check_drift_thresholds(file_equivalence, loss_ledger)
        }

        # Save diff report in JSON format
        with open(self.diff_report_json_path, 'w', encoding='utf-8') as f:
            json.dump(diff_report, f, indent=2)

        # Generate markdown report
        markdown_report = self._generate_markdown_report(diff_report)
        with open(self.diff_report_md_path, 'w', encoding='utf-8') as f:
            f.write(markdown_report)

        # Print report based on format
        if output_format == "text":
            print(self._generate_text_report(diff_report))
        elif output_format == "json":
            print(json.dumps(diff_report, indent=2))
        elif output_format == "md":
            print(markdown_report)

        return diff_report

    def _compare_with_baseline(self, baseline_id: str, top_n: int, filter_pattern: Optional[str],
                              output_format: str) -> Dict[str, Any]:
        """Compare current target semantic state to baseline target semantic state."""
        baseline_path = Path(f".maestro/convert/baselines/{baseline_id}")
        if not baseline_path.exists():
            print(f"Baseline {baseline_id} not found at {baseline_path}")
            return {}

        # Load the baseline report
        baseline_report_path = baseline_path / "diff_report.json"
        if not baseline_report_path.exists():
            print(f"Baseline report not found at {baseline_report_path}")
            return {}

        with open(baseline_report_path, 'r', encoding='utf-8') as f:
            baseline_report = json.load(f)

        # Generate current report if it doesn't exist
        if not self.diff_report_json_path.exists():
            print("Current diff report does not exist. Generating current report...")
            # Run semantic diff to generate current report
            semantic_reports = self._load_all_semantic_reports()
            task_summaries = self._load_all_task_summaries()

            if self.mapping_index_path.exists():
                with open(self.mapping_index_path, 'r', encoding='utf-8') as f:
                    mapping_index = json.load(f)
            else:
                mapping_index = self.generate_mapping_index()

            heuristics_data = self._compute_deterministic_heuristics(mapping_index, semantic_reports, task_summaries)
            file_equivalence = self._calculate_file_equivalence(semantic_reports, heuristics_data)
            concept_coverage = self._calculate_concept_coverage(semantic_reports, mapping_index)
            loss_ledger = self._build_loss_ledger(semantic_reports)
            risk_hotspots = self._identify_risk_hotspots(semantic_reports, heuristics_data, top_n)

            current_report = {
                "generated_at": datetime.now().isoformat(),
                "file_equivalence": file_equivalence,
                "concept_coverage": concept_coverage,
                "loss_ledger": loss_ledger,
                "top_risk_hotspots": risk_hotspots,
                "heuristics_evidence": heuristics_data,
            }
        else:
            with open(self.diff_report_json_path, 'r', encoding='utf-8') as f:
                current_report = json.load(f)

        # Compare the two reports to find drift
        baseline_drift_report = self._analyze_baseline_drift(baseline_report, current_report, baseline_id)

        # Save the baseline diff report
        baseline_diff_path = self.base_path / f"diff_report_baseline_{baseline_id}.json"
        with open(baseline_diff_path, 'w', encoding='utf-8') as f:
            json.dump(baseline_drift_report, f, indent=2)

        # Generate markdown report for baseline comparison
        markdown_report = self._generate_baseline_markdown_report(baseline_drift_report)
        baseline_md_path = self.base_path / f"diff_report_baseline_{baseline_id}.md"
        with open(baseline_md_path, 'w', encoding='utf-8') as f:
            f.write(markdown_report)

        # Print based on format
        if output_format == "text":
            print(self._generate_baseline_text_report(baseline_drift_report))
        elif output_format == "json":
            print(json.dumps(baseline_drift_report, indent=2))
        elif output_format == "md":
            print(markdown_report)

        return baseline_drift_report

    def _analyze_baseline_drift(self, baseline_report: Dict, current_report: Dict, baseline_id: str) -> Dict:
        """Analyze drift between baseline and current semantic state."""
        # Compare concept coverage
        baseline_cc = baseline_report.get("concept_coverage", {})
        current_cc = current_report.get("concept_coverage", {})

        preserved_change = current_cc.get("preserved_count", 0) - baseline_cc.get("preserved_count", 0)
        changed_change = current_cc.get("changed_count", 0) - baseline_cc.get("changed_count", 0)
        lost_change = current_cc.get("lost_count", 0) - baseline_cc.get("lost_count", 0)

        concept_drift = {
            "preserved_change": preserved_change,
            "changed_change": changed_change,
            "lost_change": lost_change,
            "preserved_trend": "increased" if preserved_change > 0 else "decreased" if preserved_change < 0 else "stable",
            "lost_trend": "increased" if lost_change > 0 else "decreased" if lost_change < 0 else "stable"
        }

        # Compare file equivalence
        baseline_equiv = {fe["task_id"]: fe for fe in baseline_report.get("file_equivalence", [])}
        current_equiv = {fe["task_id"]: fe for fe in current_report.get("file_equivalence", [])}

        # Find files that changed equivalence level
        equivalence_changes = []
        all_task_ids = set(baseline_equiv.keys()) | set(current_equiv.keys())

        for task_id in all_task_ids:
            baseline_fe = baseline_equiv.get(task_id)
            current_fe = current_equiv.get(task_id)

            if baseline_fe and current_fe:
                if baseline_fe.get("semantic_equivalence") != current_fe.get("semantic_equivalence"):
                    equivalence_changes.append({
                        "task_id": task_id,
                        "from": baseline_fe["semantic_equivalence"],
                        "to": current_fe["semantic_equivalence"]
                    })
            elif baseline_fe:
                # File was in baseline but not in current - removed
                equivalence_changes.append({
                    "task_id": task_id,
                    "from": baseline_fe["semantic_equivalence"],
                    "to": "removed"
                })
            elif current_fe:
                # File is in current but not in baseline - new
                equivalence_changes.append({
                    "task_id": task_id,
                    "from": "new",
                    "to": current_fe["semantic_equivalence"]
                })

        # Compare loss ledger
        baseline_loss = {entry["task_id"]: entry for entry in baseline_report.get("loss_ledger", [])}
        current_loss = {entry["task_id"]: entry for entry in current_report.get("loss_ledger", [])}

        loss_changes = []
        all_loss_task_ids = set(baseline_loss.keys()) | set(current_loss.keys())

        for task_id in all_loss_task_ids:
            baseline_entry = baseline_loss.get(task_id)
            current_entry = current_loss.get(task_id)

            if baseline_entry and current_entry:
                # Compare lost concepts
                baseline_lost = set(baseline_entry.get("lost_concepts", []))
                current_lost = set(current_entry.get("lost_concepts", []))

                new_lost = list(current_lost - baseline_lost)
                resolved_lost = list(baseline_lost - current_lost)

                if new_lost or resolved_lost:
                    loss_changes.append({
                        "task_id": task_id,
                        "new_lost": new_lost,
                        "resolved_lost": resolved_lost,
                        "total_lost_change": len(current_lost) - len(baseline_lost)
                    })
            elif baseline_entry:
                loss_changes.append({
                    "task_id": task_id,
                    "new_lost": [],
                    "resolved_lost": baseline_entry.get("lost_concepts", []),
                    "total_lost_change": -len(baseline_entry.get("lost_concepts", []))
                })
            elif current_entry:
                loss_changes.append({
                    "task_id": task_id,
                    "new_lost": current_entry.get("lost_concepts", []),
                    "resolved_lost": [],
                    "total_lost_change": len(current_entry.get("lost_concepts", []))
                })

        # Analyze drift significance
        significant_drift = (
            abs(concept_drift["lost_change"]) > 2 or  # More than 2 concepts lost/gained
            len([ec for ec in equivalence_changes if ec["to"] == "low"]) > 0 or  # New low equivalence files
            len([lc for lc in loss_changes if len(lc["new_lost"]) > 0]) > 2  # Multiple new losses
        )

        baseline_drift_report = {
            "generated_at": datetime.now().isoformat(),
            "baseline_compared": baseline_id,
            "baseline_path": baseline_report.get("baseline_path", "unknown"),
            "current_path": current_report.get("current_path", str(self.diff_report_json_path)),
            "concept_coverage_drift": concept_drift,
            "equivalence_changes": equivalence_changes,
            "loss_changes": loss_changes,
            "significant_drift_detected": significant_drift,
            "top_equivalence_changes": equivalence_changes[:10],  # Top 10 equivalence changes
            "top_loss_changes": loss_changes[:10],  # Top 10 loss changes
            "drift_summary": self._generate_drift_summary(concept_drift, equivalence_changes, loss_changes, significant_drift)
        }

        return baseline_drift_report

    def _generate_drift_summary(self, concept_drift: Dict, equivalence_changes: List[Dict], loss_changes: List[Dict], significant_drift: bool) -> str:
        """Generate a summary of the detected drift."""
        summary_parts = []

        if concept_drift["preserved_trend"] == "decreased":
            summary_parts.append(f"⚠️ {abs(concept_drift['preserved_change'])} fewer concepts are preserved compared to baseline")
        elif concept_drift["preserved_trend"] == "increased":
            summary_parts.append(f"✅ {concept_drift['preserved_change']} more concepts are preserved compared to baseline")

        if concept_drift["lost_trend"] == "increased":
            summary_parts.append(f"⚠️ {concept_drift['lost_change']} more concepts are lost compared to baseline")
        elif concept_drift["lost_trend"] == "decreased":
            summary_parts.append(f"✅ {abs(concept_drift['lost_change'])} fewer concepts are lost compared to baseline")

        low_equiv_changes = [ec for ec in equivalence_changes if ec["to"] == "low"]
        if low_equiv_changes:
            summary_parts.append(f"⚠️ {len(low_equiv_changes)} files now have low semantic equivalence (were better in baseline)")

        new_loss_changes = [lc for lc in loss_changes if len(lc["new_lost"]) > 0]
        if new_loss_changes:
            summary_parts.append(f"⚠️ {len(new_loss_changes)} files have new concept losses not present in baseline")

        if not summary_parts:
            summary_parts.append("✅ No significant semantic drift detected since baseline")

        return "; ".join(summary_parts)

    def _generate_baseline_text_report(self, baseline_report: Dict) -> str:
        """Generate a text-based baseline comparison report."""
        report = []
        report.append("Baseline Semantic Drift Report")
        report.append("=" * 40)
        report.append(f"Baseline ID: {baseline_report['baseline_compared']}")
        report.append(f"Generated at: {baseline_report['generated_at']}")
        report.append("")

        report.append("Drift Summary:")
        report.append(f"  {baseline_report['drift_summary']}")
        report.append("")

        cc_drift = baseline_report["concept_coverage_drift"]
        report.append("Concept Coverage Changes:")
        report.append(f"  Preserved: {cc_drift['preserved_change']:+d} ({cc_drift['preserved_trend']})")
        report.append(f"  Changed: {cc_drift['changed_change']:+d}")
        report.append(f"  Lost: {cc_drift['lost_change']:+d} ({cc_drift['lost_trend']})")
        report.append("")

        report.append(f"Equivalence Changes: {len(baseline_report['equivalence_changes'])} files affected")
        for ec in baseline_report['top_equivalence_changes']:
            report.append(f"  {ec['task_id']}: {ec['from']} → {ec['to']}")
        report.append("")

        report.append(f"Loss Changes: {len(baseline_report['loss_changes'])} files affected")
        for lc in baseline_report['top_loss_changes']:
            if lc['new_lost']:
                report.append(f"  {lc['task_id']}: +{len(lc['new_lost'])} lost concepts")
            if lc['resolved_lost']:
                report.append(f"  {lc['task_id']}: -{len(lc['resolved_lost'])} resolved losses")
        report.append("")

        report.append(f"Significant Drift: {'YES' if baseline_report['significant_drift_detected'] else 'NO'}")
        report.append("")

        return "\n".join(report)

    def _generate_baseline_markdown_report(self, baseline_report: Dict) -> str:
        """Generate a markdown-based baseline comparison report."""
        md = []
        md.append("# Baseline Semantic Drift Report")
        md.append(f"**Baseline ID**: {baseline_report['baseline_compared']}")
        md.append(f"**Generated at**: {baseline_report['generated_at']}")
        md.append("")

        md.append("## Drift Summary")
        md.append(baseline_report['drift_summary'])
        md.append("")

        cc_drift = baseline_report["concept_coverage_drift"]
        md.append("## Concept Coverage Changes")
        md.append("| Metric | Change | Trend |")
        md.append("|--------|--------|-------|")
        md.append(f"| Preserved | {cc_drift['preserved_change']:+d} | {cc_drift['preserved_trend']} |")
        md.append(f"| Changed | {cc_drift['changed_change']:+d} | stable |")
        md.append(f"| Lost | {cc_drift['lost_change']:+d} | {cc_drift['lost_trend']} |")
        md.append("")

        md.append("## Equivalence Changes")
        md.append(f"**Total files with equivalence changes: {len(baseline_report['equivalence_changes'])}**")
        if baseline_report['top_equivalence_changes']:
            md.append("")
            md.append("| Task ID | From | To |")
            md.append("|---------|------|-----|")
            for ec in baseline_report['top_equivalence_changes']:
                md.append(f"| {ec['task_id']} | {ec['from']} | {ec['to']} |")
        else:
            md.append("No equivalence changes detected.")
        md.append("")

        md.append("## Loss Changes")
        md.append(f"**Total files with loss changes: {len(baseline_report['loss_changes'])}**")
        if baseline_report['top_loss_changes']:
            md.append("")
            md.append("| Task ID | New Lost | Resolved |")
            md.append("|---------|----------|----------|")
            for lc in baseline_report['top_loss_changes']:
                new_count = len(lc['new_lost'])
                res_count = len(lc['resolved_lost'])
                md.append(f"| {lc['task_id']} | {new_count} | {res_count} |")
        else:
            md.append("No loss changes detected.")
        md.append("")

        md.append("## Drift Assessment")
        drift_status = "⚠️ **SIGNIFICANT DRIFT DETECTED**" if baseline_report['significant_drift_detected'] else "✅ **NO SIGNIFICANT DRIFT**"
        md.append(f"**Status**: {drift_status}")
        md.append("")

        return "\n".join(md)

    def _load_all_semantic_reports(self) -> Dict[str, Dict]:
        """Load all semantic reports from .maestro/convert/semantics/."""
        semantic_reports = {}
        semantic_dir = Path(".maestro/convert/semantics")
        
        if semantic_dir.exists():
            for sem_file in semantic_dir.glob("task_*.json"):
                task_id = sem_file.name.replace("task_", "").replace(".json", "")
                try:
                    with open(sem_file, 'r', encoding='utf-8') as f:
                        report = json.load(f)
                        semantic_reports[task_id] = report
                except json.JSONDecodeError:
                    print(f"Warning: Could not decode semantic report {sem_file}")
                    continue
        
        return semantic_reports

    def _load_all_task_summaries(self) -> Dict[str, Dict]:
        """Load all task summaries from .maestro/convert/summaries/."""
        task_summaries = {}
        summaries_dir = Path(".maestro/convert/summaries")
        
        if summaries_dir.exists():
            for summary_file in summaries_dir.glob("task_*.json"):
                task_id = summary_file.name.replace("task_", "").replace(".json", "")
                try:
                    with open(summary_file, 'r', encoding='utf-8') as f:
                        summary = json.load(f)
                        task_summaries[task_id] = summary
                except json.JSONDecodeError:
                    print(f"Warning: Could not decode task summary {summary_file}")
                    continue
        
        return task_summaries

    def _compute_deterministic_heuristics(self, mapping_index: Dict, semantic_reports: Dict, task_summaries: Dict) -> Dict:
        """Compute deterministic heuristics for semantic comparison."""
        heuristics = {
            "identifier_presence": {},
            "function_class_counts": {},
            "export_api_surface": {},
            "file_size_deltas": {},
            "dependency_graph_deltas": {}
        }

        # Process each mapped file
        for target_path, mapping_info in mapping_index.get("file_mapping", {}).items():
            source_path = mapping_info.get("source_file", "unknown")
            
            # Get source and target file content if available
            source_content = self._read_file_if_exists(source_path)
            target_content = self._read_file_if_exists(target_path)
            
            if source_content and target_content:
                # Identifier presence checks (from glossary keywords)
                glossary_entries = mapping_index.get("concept_mapping", [])
                identifiers_present = self._check_identifier_presence(
                    source_content, target_content, glossary_entries
                )
                heuristics["identifier_presence"][target_path] = identifiers_present
                
                # Function/class counts using regex
                src_func_class_count = self._count_functions_classes(source_content)
                tgt_func_class_count = self._count_functions_classes(target_content)
                heuristics["function_class_counts"][target_path] = {
                    "source_count": src_func_class_count,
                    "target_count": tgt_func_class_count,
                    "delta": tgt_func_class_count - src_func_class_count
                }
                
                # File size deltas
                heuristics["file_size_deltas"][target_path] = {
                    "source_size": len(source_content),
                    "target_size": len(target_content),
                    "delta": len(target_content) - len(source_content),
                    "ratio": len(target_content) / len(source_content) if len(source_content) > 0 else 0
                }
                
                # Dependency graph deltas (import/include counts)
                src_deps = self._extract_dependencies(source_content, source_path)
                tgt_deps = self._extract_dependencies(target_content, target_path)
                heuristics["dependency_graph_deltas"][target_path] = {
                    "source_deps_count": len(src_deps),
                    "target_deps_count": len(tgt_deps),
                    "source_deps": src_deps,
                    "target_deps": tgt_deps,
                    "delta": len(tgt_deps) - len(src_deps)
                }

        return heuristics

    def _read_file_if_exists(self, file_path: str) -> Optional[str]:
        """Read file content if it exists."""
        if file_path != "unknown" and os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
            except:
                return None
        return None

    def _check_identifier_presence(self, source_content: str, target_content: str, glossary_entries: List[Dict]) -> Dict:
        """Check if identifiers from glossary are present in target content."""
        results = {
            "total_glossary_entries": len(glossary_entries),
            "present_in_target": [],
            "missing_from_target": [],
            "mapping_violations": []  # Entries that should be mapped differently
        }
        
        for entry in glossary_entries:
            source_term = entry.get("source_term", "")
            target_term = entry.get("target_term", "")
            
            if source_term.lower() in source_content.lower():
                if target_term.lower() in target_content.lower():
                    results["present_in_target"].append(entry.get("term_id", source_term))
                else:
                    results["missing_from_target"].append({
                        "term_id": entry.get("term_id", ""),
                        "source_term": source_term,
                        "target_term": target_term
                    })
            else:
                # If source term not in source content, we might have a different issue
                pass
        
        return results

    def _count_functions_classes(self, content: str) -> int:
        """Count functions and classes using regex patterns."""
        # Simple regex-based counting - in a real implementation, this would use proper parsers
        # Match function definitions in various languages
        func_patterns = [
            r'def\s+\w+',  # Python functions
            r'function\s+\w+',  # JavaScript/other functions
            r'public\s+\w+|\w+\s+\w+\s*\([^)]*\)\s*\{',  # Java/C# methods
            r'private\s+\w+|\w+\s+\w+\s*\([^)]*\)\s*\{',  # Private methods
            r'class\s+\w+',  # Class definitions
            r'struct\s+\w+',  # Struct definitions
        ]
        
        count = 0
        for pattern in func_patterns:
            count += len(re.findall(pattern, content, re.IGNORECASE))
        
        return count

    def _extract_dependencies(self, content: str, file_path: str) -> List[str]:
        """Extract dependencies/imports from file content based on file extension."""
        ext = Path(file_path).suffix.lower()
        dependencies = []
        
        if ext in ['.py']:
            # Python imports
            imports = re.findall(r'import\s+([a-zA-Z_][a-zA-Z0-9_.]*)', content)
            from_imports = re.findall(r'from\s+([a-zA-Z_][a-zA-Z0-9_.]*)\s+import', content)
            dependencies.extend(imports)
            dependencies.extend(from_imports)
        elif ext in ['.js', '.ts', '.jsx', '.tsx']:
            # JavaScript/TypeScript imports
            imports = re.findall(r'import\s+.*?\s+from\s+[\'"]([^\'"]+)[\'"]', content)
            dependencies.extend(imports)
        elif ext in ['.java']:
            # Java imports
            imports = re.findall(r'import\s+([a-zA-Z_][a-zA-Z0-9_.]*);', content)
            dependencies.extend(imports)
        elif ext in ['.cpp', '.c', '.h', '.hpp']:
            # C++ includes
            includes = re.findall(r'#include\s+[<"]([^>"]+)[>"]', content)
            dependencies.extend(includes)
        
        return list(set(dependencies))  # Return unique dependencies

    def _calculate_file_equivalence(self, semantic_reports: Dict, heuristics_data: Dict) -> List[Dict]:
        """Calculate file-level equivalence ratings."""
        file_equivalence = []

        for task_id, report in semantic_reports.items():
            # Start with semantic equivalence from the report
            equiv_level = report.get("semantic_equivalence", "unknown")
            
            # Enhance with heuristic data if available
            heuristic_evidence = {}
            for category, data in heuristics_data.items():
                if task_id in data:
                    heuristic_evidence[category] = data[task_id]

            # Determine overall equivalence level based on both semantic and heuristic data
            file_equiv = {
                "task_id": task_id,
                "semantic_equivalence": equiv_level,
                "confidence": report.get("confidence", 0.0),
                "risk_flags": report.get("risk_flags", []),
                "heuristic_evidence": heuristic_evidence,
                "requires_human_review": report.get("requires_human_review", False)
            }

            # Adjust equivalence level based on heuristics
            if heuristic_evidence:
                # Adjust based on heuristic thresholds
                size_delta = heuristic_evidence.get("file_size_deltas", {}).get("ratio", 1.0)
                func_delta = heuristic_evidence.get("function_class_counts", {}).get("delta", 0)
                
                if size_delta < 0.1 or size_delta > 10:  # Extreme size change
                    file_equiv["heuristic_equivalence"] = "low"
                elif abs(func_delta) > 5:  # Large function count change
                    file_equiv["heuristic_equivalence"] = "medium"
                else:
                    file_equiv["heuristic_equivalence"] = "high"

            file_equivalence.append(file_equiv)

        return file_equivalence

    def _calculate_concept_coverage(self, semantic_reports: Dict, mapping_index: Dict) -> Dict:
        """Calculate concept coverage statistics."""
        total_preserved = 0
        total_changed = 0
        total_lost = 0
        all_preserved = []
        all_changed = []
        all_lost = []

        for task_id, report in semantic_reports.items():
            preserved = report.get("preserved_concepts", [])
            changed = report.get("changed_concepts", [])
            lost = report.get("lost_concepts", [])

            all_preserved.extend(preserved)
            all_changed.extend(changed)
            all_lost.extend(lost)

            total_preserved += len(preserved)
            total_changed += len(changed)
            total_lost += len(lost)

        total_concepts = total_preserved + total_changed + total_lost
        concept_coverage = {
            "total_concepts": total_concepts,
            "preserved_count": total_preserved,
            "changed_count": total_changed,
            "lost_count": total_lost,
            "preserved_percentage": (total_preserved / total_concepts * 100) if total_concepts > 0 else 0,
            "changed_percentage": (total_changed / total_concepts * 100) if total_concepts > 0 else 0,
            "lost_percentage": (total_lost / total_concepts * 100) if total_concepts > 0 else 0,
            "preserved_concepts": list(set(all_preserved)),
            "changed_concepts": list(set(all_changed)),
            "lost_concepts": list(set(all_lost))
        }

        return concept_coverage

    def _build_loss_ledger(self, semantic_reports: Dict) -> List[Dict]:
        """Build a ledger of lost/approximated concepts with evidence."""
        loss_ledger = []

        for task_id, report in semantic_reports.items():
            lost_concepts = report.get("lost_concepts", [])
            assumptions = report.get("assumptions", [])
            risk_flags = report.get("risk_flags", [])

            if lost_concepts or risk_flags:
                loss_entry = {
                    "task_id": task_id,
                    "lost_concepts": lost_concepts,
                    "assumptions": assumptions,
                    "risk_flags": risk_flags,
                    "confidence": report.get("confidence", 0.0),
                    "semantic_equivalence": report.get("semantic_equivalence", "unknown")
                }
                loss_ledger.append(loss_entry)

        return loss_ledger

    def _identify_risk_hotspots(self, semantic_reports: Dict, heuristics_data: Dict, top_n: int) -> List[Dict]:
        """Identify top risk hotspots (files + concepts)."""
        risk_hotspots = []

        for task_id, report in semantic_reports.items():
            risk_score = 0
            
            # Calculate risk based on semantic data
            if report.get("semantic_equivalence") == "low":
                risk_score += 10
            elif report.get("semantic_equivalence") == "medium":
                risk_score += 5
            
            risk_flags = report.get("risk_flags", [])
            risk_score += len(risk_flags) * 3  # Each risk flag adds 3 points
            
            if report.get("requires_human_review", False):
                risk_score += 7

            # Add heuristic-based risk
            heuristic_risk = 0
            if task_id in heuristics_data.get("file_size_deltas", {}):
                size_ratio = heuristics_data["file_size_deltas"][task_id].get("ratio", 1.0)
                if size_ratio < 0.1 or size_ratio > 10:
                    heuristic_risk += 5
            
            if task_id in heuristics_data.get("function_class_counts", {}):
                func_delta = abs(heuristics_data["function_class_counts"][task_id].get("delta", 0))
                if func_delta > 10:
                    heuristic_risk += 3
            
            risk_score += heuristic_risk

            risk_hotspots.append({
                "task_id": task_id,
                "risk_score": risk_score,
                "semantic_equivalence": report.get("semantic_equivalence"),
                "risk_flags": risk_flags,
                "requires_human_review": report.get("requires_human_review", False),
                "heuristic_risk_indicators": heuristic_risk
            })

        # Sort by risk score and return top N
        risk_hotspots.sort(key=lambda x: x["risk_score"], reverse=True)
        return risk_hotspots[:top_n]

    def _check_drift_thresholds(self, file_equivalence: List[Dict], loss_ledger: List[Dict]) -> Dict:
        """Check if drift has exceeded acceptable thresholds for checkpoint creation."""
        thresholds = {
            "core_files_low_equivalence": 0,  # This would be set based on configuration
            "lost_concepts_count_threshold": 3,  # Default threshold
            "unknown_equivalence_ratio_threshold": 0.2  # 20% threshold
        }

        low_equiv_count = sum(1 for fe in file_equivalence if fe.get("semantic_equivalence") == "low")
        unknown_equiv_count = sum(1 for fe in file_equivalence if fe.get("semantic_equivalence") == "unknown")
        total_files = len(file_equivalence)

        lost_concepts_total = sum(len(entry.get("lost_concepts", [])) for entry in loss_ledger)

        unknown_ratio = unknown_equiv_count / total_files if total_files > 0 else 0

        drift_analysis = {
            "core_files_low_equivalence": low_equiv_count,
            "low_equivalence_exceeds_threshold": low_equiv_count > thresholds["core_files_low_equivalence"],
            "lost_concepts_count": lost_concepts_total,
            "lost_concepts_exceeds_threshold": lost_concepts_total >= thresholds["lost_concepts_count_threshold"],
            "unknown_equivalence_ratio": unknown_ratio,
            "unknown_ratio_exceeds_threshold": unknown_ratio > thresholds["unknown_equivalence_ratio_threshold"],
            "requires_checkpoint": (
                low_equiv_count > thresholds["core_files_low_equivalence"] or
                lost_concepts_total >= thresholds["lost_concepts_count_threshold"] or
                unknown_ratio > thresholds["unknown_equivalence_ratio_threshold"]
            ),
            "checkpoint_reasons": []
        }

        if low_equiv_count > thresholds["core_files_low_equivalence"]:
            drift_analysis["checkpoint_reasons"].append("Low equivalence files count exceeds threshold")
        if lost_concepts_total >= thresholds["lost_concepts_count_threshold"]:
            drift_analysis["checkpoint_reasons"].append("Lost concepts count exceeds threshold")
        if unknown_ratio > thresholds["unknown_equivalence_ratio_threshold"]:
            drift_analysis["checkpoint_reasons"].append("Unknown equivalence ratio exceeds threshold")

        # Create checkpoint if thresholds are exceeded
        if drift_analysis["requires_checkpoint"]:
            self._create_checkpoint_if_needed(drift_analysis)

        return drift_analysis

    def _create_checkpoint_if_needed(self, drift_analysis: Dict):
        """Create a checkpoint if drift thresholds are exceeded and one doesn't already exist."""
        # Create checkpoints directory if it doesn't exist
        checkpoints_dir = Path(".maestro/convert/checkpoints")
        checkpoints_dir.mkdir(parents=True, exist_ok=True)

        # Generate a unique checkpoint ID based on timestamp and drift analysis
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        checkpoint_id = f"semantic_drift_{timestamp}"

        # Check if a semantic drift checkpoint already exists
        existing_checkpoints = list(checkpoints_dir.glob("semantic_drift_*.json"))
        if existing_checkpoints:
            # If there's already a semantic drift checkpoint, don't create another
            print("Semantic drift checkpoint already exists, skipping creation.")
            return

        # Create checkpoint data
        checkpoint_data = {
            "checkpoint_id": checkpoint_id,
            "created_at": datetime.now().isoformat(),
            "label": "Semantic drift checkpoint",
            "description": "Automatically created due to semantic drift detection",
            "drift_analysis": drift_analysis,
            "requires": ["semantic_ok", "human_review"],
            "status": "pending",
            "tasks_at_checkpoint": self._get_current_tasks(),
            "conversion_state": self._get_conversion_state()
        }

        # Save checkpoint
        checkpoint_path = checkpoints_dir / f"{checkpoint_id}.json"
        with open(checkpoint_path, 'w', encoding='utf-8') as f:
            json.dump(checkpoint_data, f, indent=2)

        print(f"Created semantic drift checkpoint: {checkpoint_id}")
        print(f"Checkpoint requires approval before continuing: maestro convert checkpoint approve {checkpoint_id}")
        print("Alternatively, override with: maestro convert checkpoint override --reason 'Accept risk'")

        # Exit with error code to block the pipeline
        if os.getenv("MAESTRO_BLOCK_ON_SEMANTIC_DRIFT", "true").lower() == "true":
            print("Blocking pipeline due to semantic drift checkpoint.")
            sys.exit(1)

    def _get_current_tasks(self) -> List[Dict]:
        """Get current task state for checkpoint."""
        tasks = []
        tasks_dir = Path(".maestro/convert/tasks")

        if tasks_dir.exists():
            for task_file in tasks_dir.glob("*.json"):
                try:
                    with open(task_file, 'r', encoding='utf-8') as f:
                        task = json.load(f)
                        tasks.append(task)
                except:
                    continue

        return tasks

    def _get_conversion_state(self) -> Dict:
        """Get current conversion state for checkpoint."""
        state = {
            "conversion_pipeline": self._get_current_pipeline(),
            "semantic_summary": self._get_current_semantic_summary(),
            "conversion_memory": self._get_conversion_memory_summary()
        }
        return state

    def _get_current_pipeline(self) -> Optional[Dict]:
        """Get current conversion pipeline info."""
        pipeline_files = list(Path(".maestro/convert").glob("pipeline_*.json"))
        for pf in pipeline_files:
            try:
                with open(pf, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                continue
        return None

    def _get_current_semantic_summary(self) -> Optional[Dict]:
        """Get current semantic summary."""
        summary_path = Path(".maestro/convert/semantics/summary.json")
        if summary_path.exists():
            try:
                with open(summary_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return None

    def _get_conversion_memory_summary(self) -> Dict:
        """Get conversion memory summary."""
        memory = ConversionMemory()
        try:
            decisions = memory.load_decisions()
            glossary = memory.load_glossary()
            active_decisions = memory.get_active_decisions()
            active_issues = memory.get_active_issues()

            return {
                "decisions_count": len(decisions),
                "glossary_count": len(glossary),
                "active_decisions_count": len(active_decisions),
                "active_issues_count": len(active_issues)
            }
        except:
            return {}

    def _generate_text_report(self, diff_report: Dict) -> str:
        """Generate a text-based report."""
        report = []
        report.append("Cross-Repo Semantic Diff Report")
        report.append("=" * 40)
        report.append(f"Generated at: {diff_report['generated_at']}")
        report.append("")

        # File equivalence summary
        report.append("File-Level Equivalence:")
        equiv_counts = defaultdict(int)
        for fe in diff_report["file_equivalence"]:
            equiv_level = fe.get("semantic_equivalence", "unknown")
            equiv_counts[equiv_level] += 1

        for level, count in equiv_counts.items():
            report.append(f"  {level}: {count} files")
        report.append("")

        # Concept coverage
        cc = diff_report["concept_coverage"]
        report.append("Concept Coverage:")
        report.append(f"  Preserved: {cc['preserved_count']} ({cc['preserved_percentage']:.1f}%)")
        report.append(f"  Changed: {cc['changed_count']} ({cc['changed_percentage']:.1f}%)")
        report.append(f"  Lost: {cc['lost_count']} ({cc['lost_percentage']:.1f}%)")
        report.append("")

        # Loss ledger summary
        report.append(f"Lost/Approximated Concepts: {len(diff_report['loss_ledger'])} files affected")
        report.append("")

        # Risk hotspots
        report.append("Top Risk Hotspots:")
        for i, hotspot in enumerate(diff_report["top_risk_hotspots"], 1):
            report.append(f"  {i}. {hotspot['task_id']}: Risk Score {hotspot['risk_score']}")
        report.append("")

        # Drift analysis
        drift = diff_report["drift_threshold_analysis"]
        report.append("Drift Analysis:")
        report.append(f"  Requires Checkpoint: {'YES' if drift['requires_checkpoint'] else 'NO'}")
        if drift['checkpoint_reasons']:
            report.append("  Reasons:")
            for reason in drift['checkpoint_reasons']:
                report.append(f"    - {reason}")
        report.append("")

        return "\n".join(report)

    def _generate_markdown_report(self, diff_report: Dict) -> str:
        """Generate a markdown-based report."""
        md = []
        md.append("# Cross-Repo Semantic Diff Report")
        md.append(f"Generated at: {diff_report['generated_at']}")
        md.append("")

        # File equivalence table
        md.append("## File-Level Equivalence")
        md.append("")
        md.append("| Equivalence Level | Count |")
        md.append("|-----------------|-------|")
        
        equiv_counts = defaultdict(int)
        for fe in diff_report["file_equivalence"]:
            equiv_level = fe.get("semantic_equivalence", "unknown")
            equiv_counts[equiv_level] += 1

        for level, count in equiv_counts.items():
            md.append(f"| {level.title()} | {count} |")
        md.append("")

        # Concept coverage
        cc = diff_report["concept_coverage"]
        md.append("## Concept Coverage")
        md.append("")
        md.append(f"- Preserved: {cc['preserved_count']} ({cc['preserved_percentage']:.1f}%)")
        md.append(f"- Changed: {cc['changed_count']} ({cc['changed_percentage']:.1f}%)")
        md.append(f"- Lost: {cc['lost_count']} ({cc['lost_percentage']:.1f}%)")
        md.append("")

        # Loss ledger
        md.append("## Loss Ledger")
        md.append(f"Files with lost/approximated concepts: {len(diff_report['loss_ledger'])}")
        md.append("")

        if diff_report['loss_ledger']:
            md.append("### Files with Concept Loss:")
            for entry in diff_report['loss_ledger'][:10]:  # Show top 10
                md.append(f"- **{entry['task_id']}**: {len(entry.get('lost_concepts', []))} concepts lost")
            if len(diff_report['loss_ledger']) > 10:
                md.append(f"... and {len(diff_report['loss_ledger']) - 10} more")
            md.append("")

        # Risk hotspots
        md.append("## Top Risk Hotspots")
        md.append("")
        md.append("| Rank | Task ID | Risk Score | Equivalence | Human Review |")
        md.append("|------|---------|------------|-------------|--------------|")
        
        for i, hotspot in enumerate(diff_report["top_risk_hotspots"], 1):
            md.append(f"| {i} | {hotspot['task_id']} | {hotspot['risk_score']} | {hotspot['semantic_equivalence']} | {'Yes' if hotspot['requires_human_review'] else 'No'} |")
        md.append("")

        # Drift analysis
        drift = diff_report["drift_threshold_analysis"]
        md.append("## Drift Threshold Analysis")
        md.append("")
        md.append(f"**Requires Checkpoint**: {'YES' if drift['requires_checkpoint'] else 'NO'}")
        
        if drift['checkpoint_reasons']:
            md.append("**Reasons for Checkpoint**: ")
            for reason in drift['checkpoint_reasons']:
                md.append(f"- {reason}")
        md.append("")

        # Heuristic Evidence Summary
        md.append("## Heuristic Evidence Summary")
        md.append("")
        
        heuristics = diff_report.get("heuristics_evidence", {})
        if "file_size_deltas" in heuristics:
            large_changes = []
            for file_path, data in heuristics["file_size_deltas"].items():
                if abs(data.get("delta", 0)) > 1000:  # More than 1000 bytes difference
                    large_changes.append((file_path, abs(data["delta"])))
            
            if large_changes:
                large_changes.sort(key=lambda x: x[1], reverse=True)
                md.append("### Large Size Changes (Top 5):")
                for file_path, delta in large_changes[:5]:
                    size_data = heuristics["file_size_deltas"][file_path]
                    md.append(f"- `{file_path}`: {size_data['source_size']} → {size_data['target_size']} ({'+' if delta > 0 else ''}{delta} bytes)")
        else:
            md.append("No heuristic evidence available.")
        
        md.append("")

        return "\n".join(md)

    def generate_coverage_report(self):
        """Generate and print the semantic coverage report."""
        # Load mapping index
        if self.mapping_index_path.exists():
            with open(self.mapping_index_path, 'r', encoding='utf-8') as f:
                mapping_index = json.load(f)
        else:
            # Generate mapping index if it doesn't exist
            mapping_index = self.generate_mapping_index()

        # Load all semantic reports
        semantic_reports = self._load_all_semantic_reports()

        # Calculate concept coverage
        concept_coverage = self._calculate_concept_coverage(semantic_reports, mapping_index)

        # Identify risk flags across all reports
        all_risk_flags = []
        for task_id, report in semantic_reports.items():
            all_risk_flags.extend(report.get("risk_flags", []))
        
        # Count risk flag occurrences
        risk_flag_counts = defaultdict(int)
        for flag in all_risk_flags:
            risk_flag_counts[flag] += 1
        
        # Get top risk flags
        top_risk_flags = sorted(risk_flag_counts.items(), key=lambda x: x[1], reverse=True)[:10]

        # Identify mismatched files (files with low or unknown equivalence)
        file_equivalence = self._calculate_file_equivalence(semantic_reports, {})
        mismatched_files = []
        for fe in file_equivalence:
            equiv = fe.get("semantic_equivalence", "unknown")
            if equiv in ["low", "unknown"]:
                mismatched_files.append((fe["task_id"], equiv))
        
        # Get top mismatched files
        top_mismatched = mismatched_files[:10]

        # Print coverage report
        print("Semantic Coverage Report")
        print("=" * 30)
        print(f"Glossary Concepts Total: {concept_coverage['total_concepts']}")
        print(f"Preserved: {concept_coverage['preserved_count']} ({concept_coverage['preserved_percentage']:.1f}%)")
        print(f"Changed: {concept_coverage['changed_count']} ({concept_coverage['changed_percentage']:.1f}%)")
        print(f"Lost: {concept_coverage['lost_count']} ({concept_coverage['lost_percentage']:.1f}%)")
        print("")
        
        print("Top 10 Risk Flags:")
        for flag, count in top_risk_flags:
            print(f"  {flag}: {count}")
        print("")
        
        print("Top 10 Mismatched Files:")
        for file_id, equiv in top_mismatched:
            print(f"  {file_id}: {equiv}")
        print("")


def main():
    parser = argparse.ArgumentParser(description="Cross-Repo Semantic Diff Tool")
    parser.add_argument('command', nargs='?', default='diff', help='Command to run (diff, coverage)')
    parser.add_argument('--top', type=int, default=20, help='Show top N items (default: 20)')
    parser.add_argument('--only', help='Filter results (format: file:<path> or risk:<flag>)')
    parser.add_argument('--format', choices=['text', 'json', 'md'], default='text', help='Output format (default: text)')
    parser.add_argument('--against', help='Compare against baseline ID (format: baseline:<id>)')
    
    args = parser.parse_args()

    diff_tool = CrossRepoSemanticDiff()

    if args.command == 'coverage':
        diff_tool.generate_coverage_report()
    else:  # Default to diff
        # Generate mapping index first to ensure it exists
        diff_tool.generate_mapping_index()
        
        # Run semantic diff with parameters
        diff_tool.run_semantic_diff(
            top_n=args.top,
            filter_pattern=args.only,
            output_format=args.format,
            against_baseline=args.against
        )


if __name__ == "__main__":
    main()