"""
AI Engine Selection Logic

This module implements the logic for selecting AI engines based on the
engine enablement matrix and other settings.
"""

from typing import List, Optional
from maestro.config.settings import get_settings
from maestro.engines import get_engine, Engine, EngineError
import sys


def get_eligible_engines(role: str) -> List[str]:
    """
    Get a list of engines eligible for a specific role based on the engine matrix.
    
    Args:
        role: The role to check ('planner' or 'worker')
        
    Returns:
        List of engine names eligible for the role
    """
    settings = get_settings()
    
    eligible_engines = []
    
    # Check each engine against the matrix
    engine_roles = {
        'claude': settings.ai_engines_claude,
        'codex': settings.ai_engines_codex,
        'gemini': settings.ai_engines_gemini,
        'qwen': settings.ai_engines_qwen
    }
    
    for engine_name, role_setting in engine_roles.items():
        if role_setting in ['planner', 'both'] and role == 'planner':
            eligible_engines.append(engine_name)
        elif role_setting in ['worker', 'both'] and role == 'worker':
            eligible_engines.append(engine_name)
    
    return eligible_engines


def select_engine_for_role(role: str, preferred_order: Optional[List[str]] = None) -> Engine:
    """
    Select an engine for a specific role based on the engine matrix.
    
    Args:
        role: The role to select an engine for ('planner' or 'worker')
        preferred_order: Optional custom order to try engines (defaults to built-in order)
        
    Returns:
        Selected engine instance
        
    Raises:
        ValueError: If no eligible engine is available for the role
    """
    eligible_engines = get_eligible_engines(role)
    
    if not eligible_engines:
        raise ValueError(f"No engines enabled for {role} role. Check ai.engines settings.")
    
    # Define default fallback orders
    if role == 'planner':
        default_order = preferred_order or ['codex', 'claude', 'gemini', 'qwen']
    else:  # worker
        default_order = preferred_order or ['qwen', 'gemini', 'claude', 'codex']
    
    # Find the first eligible engine in the preferred order
    for engine_name in default_order:
        if engine_name in eligible_engines:
            # Map engine names to engine identifiers for the get_engine function
            engine_map = {
                'claude': 'claude_planner' if role == 'planner' else 'claude_planner',
                'codex': 'codex_planner' if role == 'planner' else 'codex_planner',
                'gemini': 'gemini_worker' if role == 'worker' else 'gemini_worker',
                'qwen': 'qwen_worker' if role == 'worker' else 'qwen_worker'
            }
            
            engine_identifier = engine_map.get(engine_name)
            if engine_identifier:
                try:
                    return get_engine(engine_identifier)
                except KeyError:
                    continue  # Try the next engine
    
    # If we get here, we couldn't get any engine, which shouldn't happen since we verified eligibility
    raise ValueError(f"Could not select an engine for {role} role. Available: {eligible_engines}")


def get_planner_engine(preferred_order: Optional[List[str]] = None, debug: bool = False, stream_output: bool = False) -> Engine:
    """
    Get a planner engine based on the engine matrix.
    
    Args:
        preferred_order: Optional custom order to try engines
        debug: Whether to enable debug mode
        stream_output: Whether to stream output
        
    Returns:
        Planner engine instance
    """
    eligible_engines = get_eligible_engines('planner')
    
    if not eligible_engines:
        raise ValueError("No engines enabled for planner role. Check ai.engines settings.")
    
    # Define default planner order
    default_order = preferred_order or ['codex', 'claude', 'gemini', 'qwen']
    
    # Find the first eligible engine in the preferred order
    for engine_name in default_order:
        if engine_name in eligible_engines:
            # Map to the appropriate planner identifier
            if engine_name in ['claude', 'codex']:
                engine_identifier = f"{engine_name}_planner"
            else:  # gemini, qwen would also be planner if enabled
                engine_identifier = f"{engine_name}_planner"
            
            try:
                return get_engine(engine_identifier, debug=debug, stream_output=stream_output)
            except KeyError:
                continue  # Try the next engine
    
    raise ValueError(f"Could not get any planner engine. Available: {eligible_engines}")


def get_worker_engine(preferred_order: Optional[List[str]] = None, debug: bool = False, stream_output: bool = False) -> Engine:
    """
    Get a worker engine based on the engine matrix.
    
    Args:
        preferred_order: Optional custom order to try engines
        debug: Whether to enable debug mode
        stream_output: Whether to stream output
        
    Returns:
        Worker engine instance
    """
    eligible_engines = get_eligible_engines('worker')
    
    if not eligible_engines:
        raise ValueError("No engines enabled for worker role. Check ai.engines settings.")
    
    # Define default worker order
    default_order = preferred_order or ['qwen', 'gemini', 'claude', 'codex']
    
    # Find the first eligible engine in the preferred order
    for engine_name in default_order:
        if engine_name in eligible_engines:
            # Map to the appropriate worker identifier
            if engine_name in ['qwen', 'gemini']:
                engine_identifier = f"{engine_name}_worker"
            else:  # claude, codex would also be worker if enabled
                engine_identifier = f"{engine_name}_worker"
            
            try:
                return get_engine(engine_identifier, debug=debug, stream_output=stream_output)
            except KeyError:
                continue  # Try the next engine
    
    raise ValueError(f"Could not get any worker engine. Available: {eligible_engines}")


def get_qwen_engine(use_stdio_or_tcp: Optional[bool] = None, debug: bool = False, stream_output: bool = False) -> Engine:
    """
    Get a Qwen engine with the appropriate transport based on settings.

    Args:
        use_stdio_or_tcp: Override the setting for using stdio/tcp transport
        debug: Whether to enable debug mode
        stream_output: Whether to stream output

    Returns:
        Qwen engine instance
    """
    settings = get_settings()

    # Determine transport method
    use_stdio = use_stdio_or_tcp if use_stdio_or_tcp is not None else settings.ai_qwen_use_stdio_or_tcp

    if use_stdio:
        # Use stdio/tcp transport
        print(f"[DEBUG] Qwen transport: stdio/tcp (host: {settings.ai_qwen_tcp_host}, port: {settings.ai_qwen_tcp_port})" if debug else "", file=sys.stderr)
        return get_engine(
            'qwen_worker',
            debug=debug,
            stream_output=stream_output,
            use_stdio_or_tcp=True,
            tcp_host=settings.ai_qwen_tcp_host,
            tcp_port=settings.ai_qwen_tcp_port
        )
    else:
        # Use the standard binary prompt interface
        print(f"[DEBUG] Qwen transport: binary prompt" if debug else "", file=sys.stderr)
        return get_engine(
            'qwen_worker',
            debug=debug,
            stream_output=stream_output,
            use_stdio_or_tcp=False
        )