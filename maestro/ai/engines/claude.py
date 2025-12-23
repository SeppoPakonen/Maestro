"""Claude engine specification."""


def get_spec():
    """Get the specification for the Claude engine."""
    from ..types import AiEngineSpec
    
    class ClaudeEngineSpec:
        name = "claude"
        
        def get_config(self):
            return {"binary": "claude", "args": ["--print", "--output-format", "text", "--permission-mode", "bypassPermissions"]}
        
        def build_command(self, prompt_ref, opts):
            return ["claude", "--placeholder"]
        
        def validate(self):
            return True
    
    return ClaudeEngineSpec()