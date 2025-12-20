"""
Discussion session wrapper integrating with work sessions and breadcrumbs.

Provides backward compatibility with CLI3 while using the new work session infrastructure.
"""
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

from maestro.ai import (
    DiscussionMode,
    EditorDiscussion,
    ExternalCommandClient,
    TerminalDiscussion,
    build_phase_context,
    build_task_context,
    build_track_context,
)
from maestro.work_session import WorkSession, create_session
from maestro.breadcrumb import create_breadcrumb, write_breadcrumb, list_breadcrumbs, get_breadcrumb_summary
from maestro.templates.discussion import (
    TRACK_DISCUSSION_TEMPLATE,
    PHASE_DISCUSSION_TEMPLATE,
    GENERAL_DISCUSSION_TEMPLATE
)


class DiscussionSession:
    """
    Wrapper around WorkSession for discussion mode.

    Maintains CLI3 compatibility while using WS infrastructure.
    """

    def __init__(self, work_session: WorkSession, mode: str = "editor"):
        self.work_session = work_session
        self.mode = mode  # "editor" or "terminal"
        self.history = []  # Conversation history
        self.ai_client = ExternalCommandClient()

    def run_editor_mode(self):
        """
        Run discussion in editor mode.

        Process:
        1. Open $EDITOR with template
        2. User writes prompt (non-comment lines)
        3. Save and close
        4. Parse prompt
        5. Call AI
        6. Create breadcrumb
        7. Show response
        8. Repeat until /done or /quit
        """
        from maestro.ai.editor import EditorDiscussion
        
        # Create custom context that includes session info
        context = self._get_context_for_session()
        
        # Create a temporary discussion instance to leverage existing editor functionality
        temp_discussion = EditorDiscussion(context, DiscussionMode.EDITOR, self.ai_client)
        
        # Override the start method to capture breadcrumbs
        original_start = temp_discussion.start
        temp_discussion.start = self._wrap_editor_start(original_start)
        
        return temp_discussion.start()

    def run_terminal_mode(self):
        """
        Run discussion in terminal mode.

        Process:
        1. Show prompt (>)
        2. User types (Enter to send, Ctrl+J for newline)
        3. Call AI
        4. Create breadcrumb
        5. Stream response
        6. Repeat until /done or /quit
        """
        from maestro.ai.terminal import TerminalDiscussion
        
        # Create custom context that includes session info
        context = self._get_context_for_session()
        
        # Create a temporary discussion instance to leverage existing terminal functionality
        temp_discussion = TerminalDiscussion(context, DiscussionMode.TERMINAL, self.ai_client)
        
        # Override the start method to capture breadcrumbs
        original_start = temp_discussion.start
        temp_discussion.start = self._wrap_terminal_start(original_start)
        
        return temp_discussion.start()

    def _get_context_for_session(self):
        """Create the appropriate context based on the session's related entity."""
        if 'track_id' in self.work_session.related_entity:
            track_id = self.work_session.related_entity['track_id']
            return build_track_context(track_id)
        elif 'phase_id' in self.work_session.related_entity:
            phase_id = self.work_session.related_entity['phase_id']
            return build_phase_context(phase_id)
        elif 'task_id' in self.work_session.related_entity:
            task_id = self.work_session.related_entity['task_id']
            return build_task_context(task_id)
        else:
            # General discussion context
            from maestro.ai.discussion import DiscussionContext
            return DiscussionContext(
                context_type="general",
                context_id=None,
                allowed_actions=["track.add", "track.edit", "phase.add", "phase.edit", "task.add", "task.edit"],
                system_prompt="You are a project planning assistant for Maestro. This is a general discussion session."
            )

    def _wrap_editor_start(self, original_start):
        """Wrap the editor start method to create breadcrumbs for each interaction."""
        def wrapper():
            # We'll intercept the messages as they come back and create breadcrumbs for each interaction
            result = original_start()
            
            # Process each message pair (user + AI) and create breadcrumbs
            messages = result.messages
            # Skip the first system message
            for i in range(1, len(messages)):
                if messages[i]['role'] == 'user':
                    if i + 1 < len(messages) and messages[i + 1]['role'] == 'assistant':
                        user_msg = messages[i]['content']
                        ai_msg = messages[i + 1]['content']
                        
                        # Create breadcrumb for this interaction
                        breadcrumb = create_breadcrumb(
                            prompt=user_msg,
                            response=ai_msg,
                            tools_called=[],
                            files_modified=[],
                            parent_session_id=self.work_session.session_id,
                            depth_level=0,
                            model_used="claude-sonnet",  # Default model
                            token_count={"input": len(user_msg), "output": len(ai_msg)},
                            cost=None  # Will be calculated later if needed
                        )
                        
                        write_breadcrumb(breadcrumb, self.work_session.session_id)
            
            return result
        return wrapper

    def _wrap_terminal_start(self, original_start):
        """Wrap the terminal start method to create breadcrumbs for each interaction."""
        def wrapper():
            # Since we're wrapping the whole start, we'll need to modify the TerminalDiscussion
            # to allow us to hook into its processing loop. 
            # We'll intercept the messages through the same mechanism as the editor
            result = original_start()
            
            # Process each message pair (user + AI) and create breadcrumbs
            messages = result.messages
            # Skip the first system message
            for i in range(1, len(messages)):
                if messages[i]['role'] == 'user':
                    if i + 1 < len(messages) and messages[i + 1]['role'] == 'assistant':
                        user_msg = messages[i]['content']
                        ai_msg = messages[i + 1]['content']
                        
                        # Create breadcrumb for this interaction
                        breadcrumb = create_breadcrumb(
                            prompt=user_msg,
                            response=ai_msg,
                            tools_called=[],
                            files_modified=[],
                            parent_session_id=self.work_session.session_id,
                            depth_level=0,
                            model_used="claude-sonnet",  # Default model
                            token_count={"input": len(user_msg), "output": len(ai_msg)},
                            cost=None  # Will be calculated later if needed
                        )
                        
                        write_breadcrumb(breadcrumb, self.work_session.session_id)
            
            return result
        return wrapper

    def process_command(self, command: str) -> bool:
        """
        Process special commands.

        Commands:
        - /done: Complete session and generate actions
        - /quit: Cancel session
        - /save: Save current state
        - /history: Show conversation history

        Returns:
            True if session should continue, False if done
        """
        from maestro.work_session import complete_session, interrupt_session

        normalized = command.strip().lower()
        if normalized == "/done":
            self.work_session = complete_session(self.work_session)
            return False
        elif normalized == "/quit":
            self.work_session = interrupt_session(self.work_session)
            return False
        elif normalized == "/history":
            self.show_history()
            return True
        return True

    def show_history(self) -> None:
        """
        Show discussion history from breadcrumbs.
        """
        breadcrumbs = list_breadcrumbs(self.work_session.session_id)
        
        print("\n" + "="*65)
        print(f"Discussion History: {self.work_session.session_id}")
        print("="*65)
        
        for breadcrumb in breadcrumbs:
            print(f"\n[{breadcrumb.timestamp}] User:")
            print(f"  {breadcrumb.prompt}")
            print(f"\n[{breadcrumb.timestamp}] AI ({breadcrumb.model_used}):")
            print(f"  {breadcrumb.response}")
        
        summary = get_breadcrumb_summary(self.work_session.session_id)
        print(f"\nTotal interactions: {len(breadcrumbs)}")
        print(f"Total tokens: {summary['total_tokens']['input'] + summary['total_tokens']['output']:,}")
        print(f"Estimated cost: ${summary['total_cost']:.2f}")
        print()

    def generate_actions(self) -> List[Dict[str, Any]]:
        """
        Generate JSON actions from discussion.

        Uses AI to analyze conversation and propose actions.
        """
        # Get all conversation history to generate actions
        breadcrumbs = list_breadcrumbs(self.work_session.session_id)
        conversation_history = ""
        for breadcrumb in breadcrumbs:
            conversation_history += f"User: {breadcrumb.prompt}\n"
            conversation_history += f"AI: {breadcrumb.response}\n\n"
        
        if not conversation_history.strip():
            return []
        
        # Use the AI client to generate actions from the conversation
        system_prompt = f"You are analyzing a discussion to extract actionable items. Extract any JSON actions from this conversation:\n\n{conversation_history}"
        
        # Create a simple message to extract actions
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Please extract any JSON-formatted actions from this conversation: {conversation_history}"}
        ]
        
        response = self.ai_client.send_message(messages, system_prompt)
        
        # Extract JSON actions from the response
        import re
        json_pattern = r'\{[^{}]*\}|(?<=\[)[^\[\]]*(?=\])'
        matches = re.findall(r'\[.*\]', response, re.DOTALL)
        
        if matches:
            try:
                actions = json.loads(matches[0])
                if isinstance(actions, list):
                    return actions
                else:
                    return [actions]
            except json.JSONDecodeError:
                pass
        
        return []


def create_discussion_session(
    session_type: str,
    related_entity: Optional[Dict[str, Any]] = None,
    mode: str = "editor"
) -> DiscussionSession:
    """
    Create a new discussion session with work session infrastructure.
    
    Args:
        session_type: Type of discussion session (discussion)
        related_entity: Dictionary with track_id, phase_id, or task_id
        mode: Discussion mode ("editor" or "terminal")
    
    Returns:
        DiscussionSession instance
    """
    work_session = create_session(
        session_type=session_type,
        related_entity=related_entity or {},
        metadata={"discussion_mode": mode, "created_at": datetime.now().isoformat()}
    )
    
    return DiscussionSession(work_session, mode)


def resume_discussion(session_id: str) -> DiscussionSession:
    """
    Resume a previous discussion session.

    Process:
    1. Load session
    2. Load conversation history from breadcrumbs
    3. Show history
    4. Continue discussion
    5. Create new breadcrumbs
    """
    from maestro.work_session import load_session
    
    # Find and load the session
    session_path = Path("docs/sessions") / session_id / "session.json"
    work_session = load_session(session_path)
    
    # Show history
    breadcrumbs = list_breadcrumbs(session_id)
    print(f"\nResuming discussion session: {session_id}")
    print(f"Total previous interactions: {len(breadcrumbs)}")
    
    discussion_mode = work_session.metadata.get("discussion_mode", "editor")
    discussion = DiscussionSession(work_session, discussion_mode)
    
    return discussion