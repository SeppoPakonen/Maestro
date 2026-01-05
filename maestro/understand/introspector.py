"""
Introspector module for gathering project understanding data.
"""
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any


class ProjectIntrospector:
    """Introspects the Maestro project to gather understanding data."""
    
    def __init__(self):
        self.project_root = Path.cwd()
        self.maestro_dir = self.project_root / "maestro"
        
    def gather_identity(self) -> Dict[str, str]:
        """Gather identity information about Maestro."""
        identity = {
            "description": "Maestro is an AI Task Management CLI that orchestrates AI agents to work on complex projects",
            "purpose": "Conductor of AI symphonies",
            "not": "A simple task runner - it's a complex project orchestration system"
        }
        return identity
    
    def gather_authority_model(self) -> Dict[str, Any]:
        """Gather information about the authority model."""
        authority = {
            "human_control": [
                "Session management and initiation",
                "Approval of AI-generated operations",
                "Setting project goals and constraints"
            ],
            "ai_capabilities": [
                "Generating project operations through plan exploration",
                "Discussing and modifying plans",
                "Creating and refining work items"
            ],
            "autonomy_config": {
                "auto_apply": "Controls automatic application of AI-generated changes",
                "explore_sessions": "Configures iterative planning sessions",
                "engine_selection": "Allows specifying which AI engine to use"
            }
        }
        return authority
    
    def gather_rule_gates(self) -> Dict[str, Any]:
        """Gather information about rule gates and hard-stop conditions."""
        # Look for rule-related files and configurations
        rule_gates = {
            "hard_stops": [
                "Invalid JSON in operations files",
                "Schema mismatch in plan/project operations",
                "Malformed documents that can't be parsed",
                "Failed validation of operations before application"
            ],
            "enforcement_locations": [
                "maestro/plan_ops/decoder.py - JSON decoding and validation",
                "maestro/project_ops/decoder.py - Project operations validation",
                "maestro/plan_ops/executor.py - Execution validation",
                "maestro/project_ops/executor.py - Project operations execution validation"
            ]
        }
        return rule_gates
    
    def gather_mutation_boundaries(self) -> Dict[str, str]:
        """Gather information about mutation boundaries."""
        boundaries = {
            "docs_md_canonical": "Documentation files in docs/*.md are considered canonical",
            "maestro_ops_channels": "Changes to operations should go through Maestro ops commands, not direct edits",
            "ai_mutation_path": "AI may mutate through Maestro operations, but does not directly edit docs",
            "manual_edits": "Manual edits should be made to source code, not generated files"
        }
        return boundaries
    
    def gather_automation_long_run(self) -> Dict[str, Any]:
        """Gather information about automation and long-run modes."""
        # Look for explore sessions and related functionality
        automation = {
            "explore_sessions": {
                "path": "docs/sessions/explore/",
                "description": "Long-running iterative planning sessions that convert plans to project operations"
            },
            "resume_capability": {
                "command": "maestro resume <session>",
                "description": "Ability to resume interrupted sessions"
            },
            "auto_apply_flag": {
                "purpose": "Automatically apply AI-generated changes without confirmation",
                "usage": "maestro plan explore --auto-apply"
            }
        }
        return automation
    
    def gather_directory_semantics(self) -> Dict[str, str]:
        """Gather information about directory semantics."""
        semantics = {
            ".maestro/": "Project-local Maestro configuration and session data",
            "$HOME/.maestro/": "Global Maestro configuration and user settings",
            "docs/": "Documentation files and project understanding snapshots",
            "maestro/": "Maestro core codebase"
        }
        return semantics
    
    def gather_contracts(self) -> Dict[str, Any]:
        """Gather information about contracts (plan_ops and project_ops)."""
        contracts = {
            "plan_ops": {
                "kind": "plan_ops",
                "version": "1.0",
                "description": "Operations for modifying plans"
            },
            "project_ops": {
                "kind": "project_ops", 
                "version": "1.0",
                "description": "Operations for modifying project files and structure"
            }
        }
        return contracts
    
    def gather_evidence_index(self) -> List[str]:
        """Gather evidence index - mapping claims to file paths."""
        evidence = [
            "maestro/main.py - Main CLI entry point",
            "maestro/commands/ - Command implementations",
            "maestro/modules/cli_parser.py - CLI parsing logic",
            "maestro/plan_ops/ - Plan operations implementation",
            "maestro/project_ops/ - Project operations implementation",
            "docs/maestro - Task tracking",
            "maestro/config/settings.py - Configuration management",
            "maestro/plans.py - Plan storage and management",
            "maestro/session_model.py - Session management",
            "maestro/plan_explore/session.py - Explore session implementation"
        ]
        return evidence
    
    def gather_all(self) -> Dict[str, Any]:
        """Gather all project understanding data."""
        return {
            "identity": self.gather_identity(),
            "authority_model": self.gather_authority_model(),
            "rule_gates": self.gather_rule_gates(),
            "mutation_boundaries": self.gather_mutation_boundaries(),
            "automation_long_run": self.gather_automation_long_run(),
            "directory_semantics": self.gather_directory_semantics(),
            "contracts": self.gather_contracts(),
            "evidence_index": self.gather_evidence_index()
        }
