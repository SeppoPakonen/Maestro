"""Work command handlers with automatic breadcrumb creation for AI interactions."""

import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any

from ..work_session import (
    WorkSession,
    create_session,
    is_breadcrumb_enabled,
    load_breadcrumb_settings
)
from ..breadcrumb import (
    create_breadcrumb,
    write_breadcrumb,
    estimate_tokens,
    calculate_cost,
    capture_tool_call,
    track_file_modification
)
from ..engines import get_engine


def _run_ai_interaction_with_breadcrumb(
    session: WorkSession,
    prompt: str,
    model_used: str = "claude-3-5-sonnet",
    tools_called: Optional[list] = None,
    files_modified: Optional[list] = None
) -> str:
    """
    Run AI interaction with automatic breadcrumb creation.
    
    Args:
        session: The work session
        prompt: The prompt to send to the AI
        model_used: The AI model to use
        tools_called: List of tools that were called during the interaction
        files_modified: List of files that were modified during the interaction
        
    Returns:
        The AI's response
    """
    if tools_called is None:
        tools_called = []
    if files_modified is None:
        files_modified = []
    
    # Check if breadcrumbs are enabled
    if not is_breadcrumb_enabled():
        # If not enabled, just run the interaction without breadcrumbs
        engine = get_engine(model_used)
        response = engine.run(prompt)
        return response
    
    # Run the AI interaction
    try:
        engine = get_engine(model_used)
        response = engine.run(prompt)
        
        # Calculate tokens and cost
        input_tokens = estimate_tokens(prompt, model_used)
        output_tokens = estimate_tokens(response, model_used)
        cost = calculate_cost(input_tokens, output_tokens, model_used)
        
        # Create breadcrumb
        breadcrumb = create_breadcrumb(
            prompt=prompt,
            response=response,
            tools_called=tools_called,
            files_modified=files_modified,
            parent_session_id=session.parent_session_id,
            depth_level=0,  # This would need to be determined based on session hierarchy
            model_used=model_used,
            token_count={"input": input_tokens, "output": output_tokens},
            cost=cost
        )
        
        # Write breadcrumb to disk
        write_breadcrumb(breadcrumb, session.session_id)
        
        return response
    except Exception as e:
        # Create breadcrumb with error info
        breadcrumb = create_breadcrumb(
            prompt=prompt,
            response="",
            tools_called=tools_called,
            files_modified=files_modified,
            parent_session_id=session.parent_session_id,
            depth_level=0,
            model_used=model_used,
            token_count={"input": estimate_tokens(prompt, model_used), "output": 0},
            cost=0.0,
            error=str(e)
        )
        
        write_breadcrumb(breadcrumb, session.session_id)
        raise e


def handle_work_track(args) -> None:
    """Handle the 'work track' command."""
    try:
        # Create a work session for the track
        session = create_session(
            session_type="work_track",
            related_entity={"track_id": args.track_name} if args.track_name else {}
        )
        
        # Prepare the prompt for the AI
        if args.track_name:
            prompt = f"Work on the track '{args.track_name}'"
            if args.description:
                prompt += f" with description: {args.description}"
        else:
            prompt = "Start working on a new track"
        
        # Run AI interaction with breadcrumbs
        response = _run_ai_interaction_with_breadcrumb(
            session=session,
            prompt=prompt,
            model_used="claude-3-5-sonnet"
        )
        
        print(f"AI response for track work: {response}")
        
    except Exception as e:
        logging.error(f"Error in work track command: {e}")
        print(f"Error working on track: {e}")


def handle_work_phase(args) -> None:
    """Handle the 'work phase' command."""
    try:
        # Create a work session for the phase
        related_entity = {"phase_id": args.phase_name}
        if args.track:
            related_entity["track_id"] = args.track
        
        session = create_session(
            session_type="work_phase",
            related_entity=related_entity
        )
        
        # Prepare the prompt for the AI
        prompt = f"Work on the phase '{args.phase_name}'"
        if args.track:
            prompt += f" in track '{args.track}'"
        
        # Run AI interaction with breadcrumbs
        response = _run_ai_interaction_with_breadcrumb(
            session=session,
            prompt=prompt,
            model_used="claude-3-5-sonnet"
        )
        
        print(f"AI response for phase work: {response}")
        
    except Exception as e:
        logging.error(f"Error in work phase command: {e}")
        print(f"Error working on phase: {e}")


def handle_work_issue(args) -> None:
    """Handle the 'work issue' command."""
    try:
        # Create a work session for the issue
        related_entity = {"issue_id": args.issue_id}
        if args.phase:
            related_entity["phase_id"] = args.phase
        
        session = create_session(
            session_type="work_issue",
            related_entity=related_entity
        )
        
        # Prepare the prompt for the AI
        prompt = f"Work on issue '{args.issue_id}'"
        if args.phase:
            prompt += f" in phase '{args.phase}'"
        
        # Run AI interaction with breadcrumbs
        response = _run_ai_interaction_with_breadcrumb(
            session=session,
            prompt=prompt,
            model_used="claude-3-5-sonnet"
        )
        
        print(f"AI response for issue work: {response}")
        
    except Exception as e:
        logging.error(f"Error in work issue command: {e}")
        print(f"Error working on issue: {e}")


def handle_work_discuss(args) -> None:
    """Handle the 'work discuss' command."""
    try:
        # Create a work session for the discussion
        session = create_session(session_type="discussion")
        
        # Prepare the prompt for the AI
        if args.topic:
            topic_str = " ".join(args.topic)
            prompt = f"Let's discuss: {topic_str}"
        else:
            prompt = "Let's have a discussion"
        
        # Run AI interaction with breadcrumbs
        response = _run_ai_interaction_with_breadcrumb(
            session=session,
            prompt=prompt,
            model_used="claude-3-5-sonnet"
        )
        
        print(f"AI response for discussion: {response}")
        
    except Exception as e:
        logging.error(f"Error in work discuss command: {e}")
        print(f"Error in discussion: {e}")


def handle_work_analyze(args) -> None:
    """Handle the 'work analyze' command."""
    try:
        # Create a work session for the analysis
        related_entity = {}
        if args.target:
            related_entity["target"] = args.target
        
        session = create_session(
            session_type="analyze",
            related_entity=related_entity
        )
        
        # Prepare the prompt for the AI
        if args.target:
            prompt = f"Analyze the current state of '{args.target}'"
        else:
            prompt = "Analyze the current state"
        
        # Run AI interaction with breadcrumbs
        response = _run_ai_interaction_with_breadcrumb(
            session=session,
            prompt=prompt,
            model_used="claude-3-5-sonnet"
        )
        
        print(f"AI response for analysis: {response}")
        
    except Exception as e:
        logging.error(f"Error in work analyze command: {e}")
        print(f"Error in analysis: {e}")


def handle_work_fix(args) -> None:
    """Handle the 'work fix' command."""
    try:
        # Create a work session for the fix
        related_entity = {"target": args.target}
        if args.issue:
            related_entity["issue_id"] = args.issue
        
        session = create_session(
            session_type="fix",
            related_entity=related_entity
        )
        
        # Prepare the prompt for the AI
        prompt = f"Fix the issue with '{args.target}'"
        if args.issue:
            prompt += f" (issue: {args.issue})"
        
        # Run AI interaction with breadcrumbs
        response = _run_ai_interaction_with_breadcrumb(
            session=session,
            prompt=prompt,
            model_used="claude-3-5-sonnet"
        )
        
        print(f"AI response for fix: {response}")
        
    except Exception as e:
        logging.error(f"Error in work fix command: {e}")
        print(f"Error in fix: {e}")