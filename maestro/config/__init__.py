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

__all__ = [
    'Settings',
    'InvalidSettingError',
    'create_default_config',
    'get_settings',
    'set_settings'
]