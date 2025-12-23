"""AI Engine specifications package."""

from .qwen import get_spec as get_qwen_spec
from .gemini import get_spec as get_gemini_spec
from .codex import get_spec as get_codex_spec
from .claude import get_spec as get_claude_spec


def get_spec(engine_name):
    """Get the specification for an AI engine."""
    specs = {
        'qwen': get_qwen_spec,
        'gemini': get_gemini_spec,
        'codex': get_codex_spec,
        'claude': get_claude_spec,
    }
    
    if engine_name not in specs:
        raise ValueError(f"Unsupported engine: {engine_name}")
    
    return specs[engine_name]()