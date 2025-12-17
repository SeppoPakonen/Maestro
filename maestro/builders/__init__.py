"""
Maestro Builders Module

This module provides the core builder abstraction layer for the Maestro build system.
It implements the builder pattern to support multiple build systems (U++, CMake, Autotools, etc.)
as outlined in the UMK Integration Roadmap.
"""

from .base import Builder, Package
from .blitz import *
from .pch import *
from .brc import *
from .cross_compile import *
from .config import MethodConfig, BuildType, OSFamily, MethodManager, get_method, list_methods, create_default_methods, detect_and_create_methods, get_package_method_override, set_package_method_override, get_global_package_method_manager
from .host import Host, HostType, LocalHost, RemoteSSHHost, DockerHost, get_current_host, create_host
from .console import execute_command, parallel_execute
from .gcc import GccBuilder
from .msvc import MsvcBuilder
from .cmake import CMakeBuilder
from .autotools import AutotoolsBuilder
from .msbuild import MsBuildBuilder
from .maven import MavenBuilder
from .android import AndroidBuilder
from .java import JavaBuilder
from .upp import UppBuilder, UppPackage, BlitzBuilder
from .workspace import Workspace, PackageResolver, CircularDependencyError
from .cache import BuildCache, PPInfoCache, IncrementalBuilder
from .ppinfo import PPInfo
from .export import Exporter, NinjaExporter

__all__ = [
    'Builder',
    'Package',
    'MethodConfig',
    'BuildType',
    'OSFamily',
    'MethodManager',
    'get_method',
    'list_methods',
    'create_default_methods',
    'detect_and_create_methods',
    'get_package_method_override',
    'set_package_method_override',
    'get_global_package_method_manager',
    'Host',
    'HostType',
    'LocalHost',
    'RemoteSSHHost',
    'DockerHost',
    'get_current_host',
    'create_host',
    'execute_command',
    'parallel_execute',
    'GccBuilder',
    'MsvcBuilder',
    'CMakeBuilder',
    'AutotoolsBuilder',
    'MsBuildBuilder',
    'MavenBuilder',
    'AndroidBuilder',
    'JavaBuilder',
    'UppBuilder',
    'UppPackage',
    'BlitzBuilder',
    'PPInfo',
    'Workspace',
    'PackageResolver',
    'CircularDependencyError',
    'BuildCache',
    'PPInfoCache',
    'IncrementalBuilder',
    'Exporter',
    'NinjaExporter',
    'CrossCompilationConfig',
    'CrossCompilationHelper',
    'enhance_method_config_with_cross_compilation',
    'create_cross_compile_method'
]