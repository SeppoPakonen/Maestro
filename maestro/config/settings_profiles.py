"""
Settings Profiles Module for Maestro CLI

This module implements the settings profiles system for Maestro,
allowing users to save, load, and manage named configuration profiles.
"""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, asdict

from maestro.config.settings import Settings, get_settings, create_default_config


@dataclass
class ProfileMetadata:
    """Metadata for a settings profile."""
    id: str
    name: str
    created_at: str
    updated_at: str
    source_settings_version: str
    notes: Optional[str] = None


class SettingsProfileManager:
    """Manages settings profiles for Maestro CLI."""
    
    def __init__(self, base_dir: Optional[Path] = None):
        """Initialize the settings profile manager."""
        if base_dir is None:
            base_dir = Path.cwd()
        
        self.base_dir = base_dir
        self.profiles_dir = base_dir / '.maestro' / 'settings_profiles'
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        
        self.index_file = self.profiles_dir / 'index.json'
        self.profiles_subdir = self.profiles_dir / 'profiles'
        self.profiles_subdir.mkdir(exist_ok=True)
        
        self.logs_dir = base_dir / '.maestro' / 'logs'
        self.logs_dir.mkdir(exist_ok=True)
        
        # Load or initialize the index
        self.index = self._load_index()
    
    def _load_index(self) -> Dict[str, Any]:
        """Load the profile index from file."""
        if self.index_file.exists():
            with open(self.index_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # Initialize a new index
            return {
                "profiles": [],
                "active_profile_id": None,
                "default_profile_id": None
            }
    
    def _save_index(self) -> bool:
        """Save the profile index to file."""
        try:
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(self.index, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving profile index: {e}")
            return False
    
    def _get_profile_path(self, profile_id: str) -> Path:
        """Get the file path for a profile."""
        return self.profiles_subdir / f"{profile_id}.json"
    
    def _hash_settings(self, settings: Settings) -> str:
        """Create a hash of the settings to detect changes."""
        import hashlib
        settings_dict = settings.to_dict_flat()
        settings_str = json.dumps(settings_dict, sort_keys=True)
        return hashlib.md5(settings_str.encode()).hexdigest()
    
    def _save_profile(self, profile_id: str, settings: Settings) -> bool:
        """Save a settings profile to file."""
        try:
            profile_path = self._get_profile_path(profile_id)
            profile_data = {
                "settings": settings.to_dict(),
                "version": settings.maestro_version,
                "saved_at": datetime.now().isoformat()
            }
            
            with open(profile_path, 'w', encoding='utf-8') as f:
                json.dump(profile_data, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Error saving profile {profile_id}: {e}")
            return False
    
    def _load_profile(self, profile_id: str) -> Optional[Settings]:
        """Load a settings profile from file."""
        profile_path = self._get_profile_path(profile_id)
        if not profile_path.exists():
            return None
        
        try:
            with open(profile_path, 'r', encoding='utf-8') as f:
                profile_data = json.load(f)
            
            # Create a new Settings object from the profile data
            settings_data = profile_data.get("settings", {})
            
            # Flatten the nested settings structure back to individual attributes
            settings_kwargs = {}
            
            # Project Metadata
            settings_kwargs['project_id'] = settings_data.get('project_metadata', {}).get('project_id', str(uuid.uuid4()))
            settings_kwargs['created_at'] = settings_data.get('project_metadata', {}).get('created_at', datetime.now().isoformat())
            settings_kwargs['maestro_version'] = settings_data.get('project_metadata', {}).get('maestro_version', '1.2.1')
            settings_kwargs['base_dir'] = settings_data.get('project_metadata', {}).get('base_dir', str(self.base_dir))
            
            # User Preferences
            settings_kwargs['default_editor'] = settings_data.get('user_preferences', {}).get('default_editor', '$EDITOR')
            settings_kwargs['discussion_mode'] = settings_data.get('user_preferences', {}).get('discussion_mode', 'editor')
            settings_kwargs['list_format'] = settings_data.get('user_preferences', {}).get('list_format', 'table')
            
            # AI Settings
            settings_kwargs['ai_provider'] = settings_data.get('ai_settings', {}).get('ai_provider', 'anthropic')
            settings_kwargs['ai_model'] = settings_data.get('ai_settings', {}).get('ai_model', 'claude-3-5-sonnet-20250205')
            settings_kwargs['ai_api_key_file'] = settings_data.get('ai_settings', {}).get('ai_api_key_file', '~/.anthropic_key')
            settings_kwargs['ai_context_window'] = settings_data.get('ai_settings', {}).get('ai_context_window', 8192)
            settings_kwargs['ai_temperature'] = settings_data.get('ai_settings', {}).get('ai_temperature', 0.7)
            
            # AI Engine Matrix
            settings_kwargs['ai_engines_claude'] = settings_data.get('ai_settings', {}).get('ai_engines_claude', 'both')
            settings_kwargs['ai_engines_codex'] = settings_data.get('ai_settings', {}).get('ai_engines_codex', 'both')
            settings_kwargs['ai_engines_gemini'] = settings_data.get('ai_settings', {}).get('ai_engines_gemini', 'both')
            settings_kwargs['ai_engines_qwen'] = settings_data.get('ai_settings', {}).get('ai_engines_qwen', 'both')
            
            # AI Stacking Mode
            settings_kwargs['ai_stacking_mode'] = settings_data.get('ai_settings', {}).get('ai_stacking_mode', 'managed')

            # Global AI Permissions
            settings_kwargs['ai_dangerously_skip_permissions'] = settings_data.get('ai_settings', {}).get('ai_dangerously_skip_permissions', True)

            # Qwen Transport Settings
            settings_kwargs['ai_qwen_transport'] = settings_data.get('ai_settings', {}).get('ai_qwen_transport', 'cmdline')
            settings_kwargs['ai_qwen_tcp_host'] = settings_data.get('ai_settings', {}).get('ai_qwen_tcp_host', 'localhost')
            settings_kwargs['ai_qwen_tcp_port'] = settings_data.get('ai_settings', {}).get('ai_qwen_tcp_port', 7777)
            
            # Build Settings
            settings_kwargs['default_build_method'] = settings_data.get('build_settings', {}).get('default_build_method', 'auto')
            settings_kwargs['parallel_jobs'] = settings_data.get('build_settings', {}).get('parallel_jobs', 4)
            settings_kwargs['verbose_builds'] = settings_data.get('build_settings', {}).get('verbose_builds', False)
            settings_kwargs['clean_before_build'] = settings_data.get('build_settings', {}).get('clean_before_build', False)
            
            # Display Settings
            settings_kwargs['color_output'] = settings_data.get('display_settings', {}).get('color_output', True)
            settings_kwargs['unicode_symbols'] = settings_data.get('display_settings', {}).get('unicode_symbols', True)
            settings_kwargs['compact_lists'] = settings_data.get('display_settings', {}).get('compact_lists', False)
            settings_kwargs['show_completion_bars'] = settings_data.get('display_settings', {}).get('show_completion_bars', True)
            
            # Current Context
            settings_kwargs['current_track'] = settings_data.get('current_context', {}).get('current_track', None)
            settings_kwargs['current_phase'] = settings_data.get('current_context', {}).get('current_phase', None)
            settings_kwargs['current_task'] = settings_data.get('current_context', {}).get('current_task', None)
            
            return Settings(**settings_kwargs)
        except Exception as e:
            print(f"Error loading profile {profile_id}: {e}")
            return None
    
    def create_profile(self, name: str, settings: Settings, notes: Optional[str] = None) -> Optional[str]:
        """Create a new settings profile."""
        # Generate a unique profile ID
        profile_id = str(uuid.uuid4())
        
        # Create metadata
        metadata = ProfileMetadata(
            id=profile_id,
            name=name,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            source_settings_version=settings.maestro_version,
            notes=notes
        )
        
        # Add to index
        self.index["profiles"].append(asdict(metadata))
        
        # Save the profile data
        if not self._save_profile(profile_id, settings):
            # If saving failed, remove from index
            self.index["profiles"] = [p for p in self.index["profiles"] if p["id"] != profile_id]
            return None
        
        # Save index
        if not self._save_index():
            return None
        
        return profile_id
    
    def update_profile(self, profile_id: str, settings: Settings, notes: Optional[str] = None) -> bool:
        """Update an existing settings profile."""
        # Find the profile in the index
        profile_idx = None
        for i, profile in enumerate(self.index["profiles"]):
            if profile["id"] == profile_id:
                profile_idx = i
                break
        
        if profile_idx is None:
            return False
        
        # Update the profile metadata
        profile = self.index["profiles"][profile_idx]
        profile["updated_at"] = datetime.now().isoformat()
        if notes is not None:
            profile["notes"] = notes
        
        # Save the profile data
        if not self._save_profile(profile_id, settings):
            return False
        
        # Save index
        return self._save_index()
    
    def delete_profile(self, profile_id: str) -> bool:
        """Delete a settings profile."""
        # Remove from index
        self.index["profiles"] = [p for p in self.index["profiles"] if p["id"] != profile_id]
        
        # Remove the profile file
        profile_path = self._get_profile_path(profile_id)
        if profile_path.exists():
            profile_path.unlink()
        
        # Update active and default profile IDs if needed
        if self.index["active_profile_id"] == profile_id:
            self.index["active_profile_id"] = None
        if self.index["default_profile_id"] == profile_id:
            self.index["default_profile_id"] = None
        
        # Save index
        return self._save_index()
    
    def list_profiles(self) -> List[Dict[str, Any]]:
        """List all profiles."""
        return self.index["profiles"]
    
    def get_profile_by_id(self, profile_id: str) -> Optional[Dict[str, Any]]:
        """Get a profile by ID."""
        for profile in self.index["profiles"]:
            if profile["id"] == profile_id:
                return profile
        return None
    
    def get_profile_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a profile by name."""
        for profile in self.index["profiles"]:
            if profile["name"] == name:
                return profile
        return None
    
    def get_profile_by_number(self, number: int) -> Optional[Dict[str, Any]]:
        """Get a profile by number (1-indexed)."""
        profiles = self.list_profiles()
        if 1 <= number <= len(profiles):
            return profiles[number - 1]
        return None
    
    def get_active_profile(self) -> Optional[Dict[str, Any]]:
        """Get the active profile."""
        if self.index["active_profile_id"]:
            return self.get_profile_by_id(self.index["active_profile_id"])
        return None
    
    def get_default_profile(self) -> Optional[Dict[str, Any]]:
        """Get the default profile."""
        if self.index["default_profile_id"]:
            return self.get_profile_by_id(self.index["default_profile_id"])
        return None
    
    def set_active_profile(self, profile_id: str) -> bool:
        """Set the active profile."""
        if self.get_profile_by_id(profile_id):
            self.index["active_profile_id"] = profile_id
            return self._save_index()
        return False
    
    def set_default_profile(self, profile_id: str) -> bool:
        """Set the default profile."""
        if self.get_profile_by_id(profile_id):
            self.index["default_profile_id"] = profile_id
            return self._save_index()
        return False
    
    def load_profile(self, profile_id: str) -> Optional[Settings]:
        """Load settings from a profile."""
        settings = self._load_profile(profile_id)
        if settings:
            # Update the active profile
            self.set_active_profile(profile_id)
        return settings
    
    def save_current_settings(self, profile_id: str, notes: Optional[str] = None) -> bool:
        """Save the current active settings to a profile."""
        config_path = self.base_dir / "docs" / "config.md"
        current_settings = Settings.load(config_path)
        return self.update_profile(profile_id, current_settings, notes)
    
    def get_settings_hash(self) -> str:
        """Get the hash of the current active settings."""
        config_path = self.base_dir / "docs" / "config.md"
        current_settings = Settings.load(config_path)
        return self._hash_settings(current_settings)
    
    def get_profile_hash(self, profile_id: str) -> Optional[str]:
        """Get the hash of a profile's settings."""
        profile_settings = self._load_profile(profile_id)
        if profile_settings:
            return self._hash_settings(profile_settings)
        return None
    
    def create_audit_log(self, previous_settings_hash: str, new_settings_hash: str, 
                         profile_id: str, profile_name: str, diff_summary: str = "") -> bool:
        """Create an audit log entry for profile operations."""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            log_filename = f"settings_profile_{timestamp}.json"
            log_path = self.logs_dir / log_filename
            
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "operation": "profile_load",
                "profile_id": profile_id,
                "profile_name": profile_name,
                "previous_settings_hash": previous_settings_hash,
                "new_settings_hash": new_settings_hash,
                "diff_summary": diff_summary
            }
            
            with open(log_path, 'w', encoding='utf-8') as f:
                json.dump(log_entry, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Error creating audit log: {e}")
            return False
    
    def has_unsaved_changes(self) -> bool:
        """Check if current settings have unsaved changes compared to active profile."""
        active_profile = self.get_active_profile()
        if not active_profile:
            # No active profile, so no basis for comparison
            return False
        
        current_hash = self.get_settings_hash()
        profile_hash = self.get_profile_hash(active_profile["id"])
        
        return current_hash != profile_hash
