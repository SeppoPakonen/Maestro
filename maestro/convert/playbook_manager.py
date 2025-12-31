#!/usr/bin/env python3
"""
Playbook Manager - Handles human-authored conversion playbooks for Maestro.

This module implements the playbook system that allows users to encode architectural intent once
and reuse it safely across conversions. Playbooks constrain and guide planning, semantic mapping,
lowering strategies, and validation in a structured, versioned way.
"""

import os
import json
import hashlib
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
try:
    import jsonschema
except ModuleNotFoundError:  # Optional dependency for test environments
    jsonschema = None


# Playbook schema definition
PLAYBOOK_SCHEMA = {
    "type": "object",
    "required": ["id", "title", "applies_to", "intent", "principles", "version"],
    "properties": {
        "id": {"type": "string", "pattern": "^[a-zA-Z0-9_-]+$"},
        "title": {"type": "string"},
        "version": {"type": "string", "pattern": r"^\d+\.\d+$"},
        "applies_to": {
            "type": "object",
            "required": ["source_language", "target_language"],
            "properties": {
                "source_language": {"type": "string"},
                "target_language": {"type": "string"}
            }
        },
        "intent": {
            "type": "string",
            "enum": ["high_to_low_level", "low_to_high_level", "language_to_language", 
                    "platform_to_platform", "framework_to_framework", "dialect_or_library_shift"]
        },
        "principles": {
            "type": "array",
            "items": {"type": "string"}
        },
        "required_losses": {
            "type": "array",
            "items": {"type": "string"}
        },
        "forbidden_constructs": {
            "type": "object",
            "properties": {
                "target": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            }
        },
        "preferred_patterns": {
            "type": "array",
            "items": {"type": "string"}
        },
        "checkpoint_policy": {
            "type": "object",
            "properties": {
                "after_files": {"type": "integer"},
                "on_semantic_loss": {"type": "boolean"}
            }
        },
        "validation_policy": {
            "type": "object",
            "properties": {
                "mode": {"type": "string", "enum": ["vectors_only", "full", "minimal"]},
                "require_behavior_envelope": {"type": "boolean"}
            }
        }
    }
}


def _validate_playbook(playbook_data: Dict[str, Any]) -> None:
    if jsonschema is None:
        return
    jsonschema.validate(instance=playbook_data, schema=PLAYBOOK_SCHEMA)


class Playbook:
    """Represents a conversion playbook with all its constraints and policies."""
    
    def __init__(self, data: Dict[str, Any]):
        self.id = data.get('id')
        self.title = data.get('title')
        self.version = data.get('version')
        self.applies_to = data.get('applies_to', {})
        self.intent = data.get('intent')
        self.principles = data.get('principles', [])
        self.required_losses = data.get('required_losses', [])
        self.forbidden_constructs = data.get('forbidden_constructs', {})
        self.preferred_patterns = data.get('preferred_patterns', [])
        self.checkpoint_policy = data.get('checkpoint_policy', {})
        self.validation_policy = data.get('validation_policy', {})
        self.glossary = data.get('glossary', {})
        self.constraints = data.get('constraints', {})

    def to_dict(self) -> Dict[str, Any]:
        """Convert playbook to dictionary representation."""
        return {
            'id': self.id,
            'title': self.title,
            'version': self.version,
            'applies_to': self.applies_to,
            'intent': self.intent,
            'principles': self.principles,
            'required_losses': self.required_losses,
            'forbidden_constructs': self.forbidden_constructs,
            'preferred_patterns': self.preferred_patterns,
            'checkpoint_policy': self.checkpoint_policy,
            'validation_policy': self.validation_policy,
            'glossary': self.glossary,
            'constraints': self.constraints
        }

    def get_version_hash(self) -> str:
        """Get a hash representing this playbook version."""
        data_str = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()[:16]


class PlaybookManager:
    """Manages conversion playbooks including storage, retrieval, and binding."""
    
    def __init__(self, base_path: str = ".maestro"):
        self.base_path = Path(base_path)
        self.playbooks_dir = self.base_path / "playbooks"
        self.binding_file = self.base_path / "convert" / "playbook_binding.json"
        
        # Create directories if they don't exist
        self.playbooks_dir.mkdir(parents=True, exist_ok=True)

    def create_playbook(self, playbook_data: Dict[str, Any]) -> bool:
        """Create a new playbook from data."""
        try:
            # Validate the playbook data against schema
            _validate_playbook(playbook_data)
            
            # Create playbook directory
            playbook_id = playbook_data['id']
            playbook_dir = self.playbooks_dir / playbook_id
            playbook_dir.mkdir(exist_ok=True)
            
            # Save the playbook file
            playbook_file = playbook_dir / "playbook.json"
            with open(playbook_file, 'w', encoding='utf-8') as f:
                json.dump(playbook_data, f, indent=2)
                
            return True
        except Exception as e:
            if jsonschema is not None and isinstance(e, jsonschema.ValidationError):
                print(f"Playbook validation error: {e}")
                return False
            print(f"Error creating playbook: {e}")
            return False

    def load_playbook(self, playbook_id: str) -> Optional[Playbook]:
        """Load a playbook by ID."""
        try:
            playbook_file = self.playbooks_dir / playbook_id / "playbook.json"
            if not playbook_file.exists():
                return None
                
            with open(playbook_file, 'r', encoding='utf-8') as f:
                playbook_data = json.load(f)
                
            # Validate the loaded playbook
            _validate_playbook(playbook_data)
            return Playbook(playbook_data)
        except Exception as e:
            if jsonschema is not None and isinstance(e, jsonschema.ValidationError):
                print(f"Playbook validation error: {e}")
                return None
            print(f"Error loading playbook {playbook_id}: {e}")
            return None

    def list_playbooks(self) -> List[Dict[str, Any]]:
        """List all available playbooks."""
        playbooks = []
        for playbook_dir in self.playbooks_dir.iterdir():
            if playbook_dir.is_dir():
                playbook_file = playbook_dir / "playbook.json"
                if playbook_file.exists():
                    try:
                        with open(playbook_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            playbooks.append({
                                'id': data.get('id'),
                                'title': data.get('title'),
                                'version': data.get('version'),
                                'source_language': data.get('applies_to', {}).get('source_language'),
                                'target_language': data.get('applies_to', {}).get('target_language')
                            })
                    except Exception as e:
                        print(f"Error loading playbook from {playbook_dir}: {e}")
        return playbooks

    def show_playbook(self, playbook_id: str) -> Optional[Dict[str, Any]]:
        """Show detailed information about a playbook."""
        return self.load_playbook(playbook_id).to_dict() if self.load_playbook(playbook_id) else None

    def bind_playbook(self, playbook_id: str) -> bool:
        """Bind a playbook to the current conversion."""
        try:
            playbook = self.load_playbook(playbook_id)
            if not playbook:
                print(f"Playbook '{playbook_id}' not found")
                return False
            
            # Ensure convert directory exists
            (self.base_path / "convert").mkdir(exist_ok=True)
            
            # Create binding record
            binding_data = {
                'playbook_id': playbook_id,
                'playbook_version': playbook.version,
                'version_hash': playbook.get_version_hash(),
                'bound_at': int(time.time()),
                'bound_by': os.environ.get('USER', 'unknown')
            }
            
            with open(self.binding_file, 'w', encoding='utf-8') as f:
                json.dump(binding_data, f, indent=2)
                
            return True
        except Exception as e:
            print(f"Error binding playbook: {e}")
            return False

    def get_active_playbook_binding(self) -> Optional[Dict[str, Any]]:
        """Get the currently active playbook binding."""
        if not self.binding_file.exists():
            return None
            
        try:
            with open(self.binding_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading playbook binding: {e}")
            return None

    def validate_playbook_against_binding(self, playbook: Playbook) -> bool:
        """Validate that a playbook matches the current binding."""
        binding = self.get_active_playbook_binding()
        if not binding:
            return True  # No binding means no validation needed

        # Check ID and version match
        return (binding['playbook_id'] == playbook.id and
                binding['playbook_version'] == playbook.version and
                binding['version_hash'] == playbook.get_version_hash())

    def get_override_file_path(self) -> Path:
        """Get the path for the override file."""
        return self.base_path / "convert" / "playbook_overrides.json"

    def record_override(self, task_id: str, violation_type: str, reason: str) -> bool:
        """Record a playbook violation override."""
        try:
            override_file = self.get_override_file_path()

            # Ensure parent directories exist
            override_file.parent.mkdir(parents=True, exist_ok=True)

            overrides = []

            # Load existing overrides if file exists
            if override_file.exists():
                with open(override_file, 'r', encoding='utf-8') as f:
                    overrides = json.load(f)

            # Create new override record
            override_record = {
                'task_id': task_id,
                'violation_type': violation_type,
                'reason': reason,
                'timestamp': int(time.time()),
                'overridden_by': os.environ.get('USER', 'unknown')
            }

            overrides.append(override_record)

            # Write all overrides back to file
            with open(override_file, 'w', encoding='utf-8') as f:
                json.dump(overrides, f, indent=2)

            return True
        except Exception as e:
            print(f"Error recording override: {e}")
            return False

    def get_overrides(self) -> List[Dict[str, Any]]:
        """Get all recorded overrides."""
        try:
            override_file = self.get_override_file_path()
            if not override_file.exists():
                return []

            with open(override_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading overrides: {e}")
            return []


def validate_playbook_data(playbook_data: Dict[str, Any]) -> List[str]:
    """Validate playbook data against schema and return list of errors."""
    errors = []
    try:
        jsonschema.validate(instance=playbook_data, schema=PLAYBOOK_SCHEMA)
    except jsonschema.ValidationError as e:
        errors.append(f"Schema validation failed: {e.message}")
    except Exception as e:
        errors.append(f"Validation error: {e}")
    
    return errors
