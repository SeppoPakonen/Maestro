"""Session management for AI engines."""

import json
from pathlib import Path
from typing import Dict, Optional, Any
from datetime import datetime
from .types import AiEngineName


class AISessionManager:
    """Manages AI session persistence per engine."""
    
    def __init__(self, state_file: Path = Path("docs/state/ai_sessions.json")):
        self.state_file = state_file
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        
    def load_sessions(self) -> Dict[str, Any]:
        """Load session data from the state file."""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                # If there's an error loading the file, return empty dict
                return {}
        return {}
    
    def save_sessions(self, sessions: Dict[str, Any]) -> None:
        """Save session data to the state file."""
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(sessions, f, indent=2, ensure_ascii=False)
    
    def get_last_session_id(self, engine: AiEngineName) -> Optional[str]:
        """Get the last session ID for an engine."""
        sessions = self.load_sessions()
        engine_data = sessions.get(engine, {})
        return engine_data.get('last_session_id')
    
    def update_session(self, engine: AiEngineName, session_id: Optional[str], 
                      model: Optional[str] = None, danger_mode: bool = False) -> None:
        """Update the last session ID for an engine."""
        if session_id is None:
            return
            
        sessions = self.load_sessions()
        
        # Initialize engine data if not present
        if engine not in sessions:
            sessions[engine] = {}
            
        # Update the engine's session data
        sessions[engine].update({
            'last_session_id': session_id,
            'updated_at': datetime.now().isoformat(),
            'model': model,
            'danger_mode': danger_mode
        })
        
        self.save_sessions(sessions)


def extract_session_id(engine: AiEngineName, parsed_events: Optional[list] = None) -> Optional[str]:
    """
    Extract session ID from engine-specific parsed events or JSON.
    
    Args:
        engine: The AI engine name
        parsed_events: List of parsed JSON events from the engine
        
    Returns:
        Session ID if found, None otherwise
    """
    if not parsed_events:
        return None
    
    # Look for session ID in the parsed events
    for event in parsed_events:
        if isinstance(event, dict):
            # Check for various possible session ID field names
            for key in ['session_id', 'sessionId', 'session', 'id']:
                if key in event and event[key]:
                    return str(event[key])
            
            # Check for session info in nested structures
            if 'metadata' in event and isinstance(event['metadata'], dict):
                for key in ['session_id', 'sessionId', 'session', 'id']:
                    if key in event['metadata'] and event['metadata'][key]:
                        return str(event['metadata'][key])
    
    return None