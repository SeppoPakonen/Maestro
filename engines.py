#!/usr/bin/env python3
"""
Engine abstraction for LLM backends.

This module defines the interface and dummy implementations for various LLM engines
used in the orchestrator system.
"""
from typing import Protocol


# Define symbolic engine names
CODEX_PLANNER = "codex_planner"
CLAUDE_PLANNER = "claude_planner"
QWEN_WORKER = "qwen_worker"
GEMINI_WORKER = "gemini_worker"


class Engine(Protocol):
    """
    Protocol defining the interface for LLM engines.
    """
    name: str
    
    def generate(self, prompt: str) -> str:
        """
        Generate a response based on the given prompt.
        
        Args:
            prompt: The input prompt string
            
        Returns:
            The generated response string
        """
        ...


class CodexPlannerEngine:
    """
    Dummy implementation for the codex planner engine.
    """
    def __init__(self):
        self.name = CODEX_PLANNER
    
    def generate(self, prompt: str) -> str:
        """
        Generate a response simulating the codex planner.
        
        Args:
            prompt: The input prompt string
            
        Returns:
            A simulated response string
        """
        return f"[{self.name.upper()} SIMULATION]\n{prompt}"


class ClaudePlannerEngine:
    """
    Dummy implementation for the claude planner engine.
    """
    def __init__(self):
        self.name = CLAUDE_PLANNER
    
    def generate(self, prompt: str) -> str:
        """
        Generate a response simulating the claude planner.
        
        Args:
            prompt: The input prompt string
            
        Returns:
            A simulated response string
        """
        return f"[{self.name.upper()} SIMULATION]\n{prompt}"


class QwenWorkerEngine:
    """
    Dummy implementation for the qwen worker engine.
    """
    def __init__(self):
        self.name = QWEN_WORKER
    
    def generate(self, prompt: str) -> str:
        """
        Generate a response simulating the qwen worker.
        
        Args:
            prompt: The input prompt string
            
        Returns:
            A simulated response string
        """
        return f"[{self.name.upper()} SIMULATION]\n{prompt}"


class GeminiWorkerEngine:
    """
    Dummy implementation for the gemini worker engine.
    """
    def __init__(self):
        self.name = GEMINI_WORKER
    
    def generate(self, prompt: str) -> str:
        """
        Generate a response simulating the gemini worker.
        
        Args:
            prompt: The input prompt string
            
        Returns:
            A simulated response string
        """
        return f"[{self.name.upper()} SIMULATION]\n{prompt}"


def get_engine(name: str) -> Engine:
    """
    Registry function to get an engine instance by name.
    
    Args:
        name: The name of the engine to retrieve
        
    Returns:
        An instance of the requested engine
    """
    if name == CODEX_PLANNER:
        return CodexPlannerEngine()
    elif name == CLAUDE_PLANNER:
        return ClaudePlannerEngine()
    elif name == QWEN_WORKER:
        return QwenWorkerEngine()
    elif name == GEMINI_WORKER:
        return GeminiWorkerEngine()
    else:
        raise ValueError(f"Unknown engine name: {name}")


if __name__ == "__main__":
    # Test block to run each engine and print simulated output
    engines_to_test = [CODEX_PLANNER, CLAUDE_PLANNER, QWEN_WORKER, GEMINI_WORKER]
    test_prompt = "This is a test prompt to verify the engine functionality."
    
    print("Testing all engines with the same prompt:")
    print(f"Prompt: {test_prompt}")
    print("\nResults:")
    
    for engine_name in engines_to_test:
        engine = get_engine(engine_name)
        result = engine.generate(test_prompt)
        print(f"\nEngine: {engine_name}")
        print(f"Output:\n{result}")