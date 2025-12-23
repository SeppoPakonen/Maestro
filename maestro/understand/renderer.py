"""
Markdown renderer for project understanding snapshots.
"""
from typing import Dict, Any, List
from .introspector import ProjectIntrospector


class MarkdownRenderer:
    """Renders project understanding data as markdown."""
    
    def __init__(self, introspector: ProjectIntrospector):
        self.introspector = introspector
    
    def render(self) -> str:
        """Render the complete project understanding snapshot."""
        data = self.introspector.gather_all()
        
        markdown_parts = [
            "# Maestro Project Understanding Snapshot",
            "",
            "This snapshot is automatically generated from the actual code/config/docs, not narrative assumptions.",
            "Last updated: " + self._get_current_timestamp(),
            "",
            self._render_identity(data["identity"]),
            self._render_authority_model(data["authority_model"]),
            self._render_rule_gates(data["rule_gates"]),
            self._render_mutation_boundaries(data["mutation_boundaries"]),
            self._render_automation_long_run(data["automation_long_run"]),
            self._render_directory_semantics(data["directory_semantics"]),
            self._render_contracts(data["contracts"]),
            self._render_evidence_index(data["evidence_index"]),
        ]
        
        return "\n".join(markdown_parts)
    
    def _get_current_timestamp(self) -> str:
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def _render_identity(self, identity: Dict[str, str]) -> str:
        """Render the identity section."""
        parts = [
            "## Identity",
            "",
            identity.get("description", "unknown"),
            "",
            "**What Maestro is not:**",
            identity.get("not", "unknown"),
            ""
        ]
        return "\n".join(parts)
    
    def _render_authority_model(self, authority: Dict[str, Any]) -> str:
        """Render the authority model section."""
        parts = [
            "## Authority Model",
            "",
            "### What humans control:",
        ]
        
        for item in authority.get("human_control", []):
            parts.append(f"- {item}")
        
        parts.extend([
            "",
            "### What AI can do:",
        ])
        
        for item in authority.get("ai_capabilities", []):
            parts.append(f"- {item}")
        
        parts.extend([
            "",
            "### How autonomy is configured (project-dependent):",
        ])
        
        for key, value in authority.get("autonomy_config", {}).items():
            parts.append(f"- **{key}**: {value}")
        
        parts.append("")
        return "\n".join(parts)
    
    def _render_rule_gates(self, rule_gates: Dict[str, Any]) -> str:
        """Render the rule gates section."""
        parts = [
            "## Assertive Rule Gates",
            "",
            "### Hard-stop conditions:",
        ]
        
        for item in rule_gates.get("hard_stops", []):
            parts.append(f"- {item}")
        
        parts.extend([
            "",
            "### Where enforced in code:",
        ])
        
        for item in rule_gates.get("enforcement_locations", []):
            parts.append(f"- {item}")
        
        parts.append("")
        return "\n".join(parts)
    
    def _render_mutation_boundaries(self, boundaries: Dict[str, str]) -> str:
        """Render the mutation boundaries section."""
        parts = [
            "## Mutation Boundaries",
            ""
        ]
        
        for key, value in boundaries.items():
            parts.append(f"- **{key}**: {value}")
        
        parts.append("")
        return "\n".join(parts)
    
    def _render_automation_long_run(self, automation: Dict[str, Any]) -> str:
        """Render the automation and long-run mode section."""
        parts = [
            "## Automation & Long-Run Mode",
            ""
        ]
        
        explore_sessions = automation.get("explore_sessions", {})
        if explore_sessions:
            parts.extend([
                f"### Explore Sessions",
                f"- **Path**: `{explore_sessions.get('path', 'unknown')}`",
                f"- **Description**: {explore_sessions.get('description', 'unknown')}",
                ""
            ])
        
        resume_capability = automation.get("resume_capability", {})
        if resume_capability:
            parts.extend([
                f"### Resume Capability",
                f"- **Command**: `{resume_capability.get('command', 'unknown')}`",
                f"- **Description**: {resume_capability.get('description', 'unknown')}",
                ""
            ])
        
        auto_apply_flag = automation.get("auto_apply_flag", {})
        if auto_apply_flag:
            parts.extend([
                f"### Auto-Apply Flag",
                f"- **Purpose**: {auto_apply_flag.get('purpose', 'unknown')}",
                f"- **Usage**: `{auto_apply_flag.get('usage', 'unknown')}`",
                ""
            ])
        
        return "\n".join(parts)
    
    def _render_directory_semantics(self, semantics: Dict[str, str]) -> str:
        """Render the directory semantics section."""
        parts = [
            "## Directory Semantics",
            ""
        ]
        
        for key, value in semantics.items():
            parts.append(f"- **{key}**: {value}")
        
        parts.append("")
        return "\n".join(parts)
    
    def _render_contracts(self, contracts: Dict[str, Any]) -> str:
        """Render the contracts section."""
        parts = [
            "## Contracts",
            ""
        ]
        
        for contract_name, details in contracts.items():
            parts.extend([
                f"### {contract_name.upper()}",
                f"- **kind**: `{details.get('kind', 'unknown')}`",
                f"- **version**: `{details.get('version', 'unknown')}`",
                f"- **description**: {details.get('description', 'unknown')}",
                ""
            ])
        
        return "\n".join(parts)
    
    def _render_evidence_index(self, evidence: List[str]) -> str:
        """Render the evidence index section."""
        parts = [
            "## Evidence Index",
            "",
            "Claims mapped to file path references:",
        ]
        
        for item in evidence:
            parts.append(f"- {item}")
        
        parts.append("")
        return "\n".join(parts)