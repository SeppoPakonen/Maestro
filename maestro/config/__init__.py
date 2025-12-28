"""
Package init file for maestro.config module.
Exports the Settings class and related functions.
"""

from .settings import (
    Settings,
    InvalidSettingError,
    create_default_config,
    get_settings,
    set_settings
)
from .paths import (
    get_docs_root,
    get_lock_dir,
    get_ai_logs_dir,
    get_state_dir
)

__all__ = [
    'Settings',
    'InvalidSettingError',
    'create_default_config',
    'get_settings',
    'set_settings',
    'get_docs_root',
    'get_lock_dir',
    'get_ai_logs_dir',
    'get_state_dir'
]