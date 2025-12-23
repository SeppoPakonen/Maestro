"""Gemini engine specification."""


def get_spec():
    """Get the specification for the Gemini engine."""
    from ..types import AiEngineSpec
    
    class GeminiEngineSpec:
        name = "gemini"
        
        def get_config(self):
            return {"binary": "gemini", "args": ["--approval-mode", "yolo"]}
        
        def build_command(self, prompt_ref, opts):
            return ["gemini", "--placeholder"]
        
        def validate(self):
            return True
    
    return GeminiEngineSpec()