"""Codex engine specification."""


def get_spec():
    """Get the specification for the Codex engine."""
    from ..types import AiEngineSpec
    
    class CodexEngineSpec:
        name = "codex"
        
        def get_config(self):
            return {"binary": "codex", "args": ["exec", "--dangerously-bypass-approvals-and-sandbox"]}
        
        def build_command(self, prompt_ref, opts):
            return ["codex", "--placeholder"]
        
        def validate(self):
            return True
    
    return CodexEngineSpec()