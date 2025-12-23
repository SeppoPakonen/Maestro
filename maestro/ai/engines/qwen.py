"""Qwen engine specification."""


def get_spec():
    """Get the specification for the Qwen engine."""
    from ..types import AiEngineSpec
    
    class QwenEngineSpec:
        name = "qwen"
        
        def get_config(self):
            return {"binary": "qwen", "args": ["--yolo"]}
        
        def build_command(self, prompt_ref, opts):
            return ["qwen", "--placeholder"]
        
        def validate(self):
            return True
    
    return QwenEngineSpec()