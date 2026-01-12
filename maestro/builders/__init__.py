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
from .config import BuildMethod, MethodConfig, BuildType, OSFamily, MethodManager, get_method, list_methods, create_default_methods, detect_and_create_methods, get_package_method_override, set_package_method_override, get_global_package_method_manager
from .host import Host, HostType, LocalHost, RemoteSSHHost, DockerHost, get_current_host, create_host
from .console import execute_command, parallel_execute
from .gcc import GccBuilder
from .msvc import MsvcBuilder
from .cmake import CMakeBuilder
from .autotools import AutotoolsBuilder
from .msbuild import MsBuildBuilder
from .maven import MavenBuilder
from .gradle import GradleBuilder
from .android import AndroidBuilder
from .java import JavaBuilder
from .makefile import MakefileBuilder
from .upp import UppBuilder, UppPackage, BlitzBuilder
from .workspace import Workspace, PackageResolver, CircularDependencyError
from .cache import BuildCache, PPInfoCache, IncrementalBuilder
from .ppinfo import PPInfo
from .export import Exporter, NinjaExporter
from .builder_selector import select_builder, get_builder_by_name, get_available_builders, validate_builder_compatibility, select_builder_function
from .build_session import BuildSession, BuildSessionManager, BuildStepResult, BuildStatus, should_continue_on_error, get_resume_package
from .artifact_manager import ArtifactManager, ArtifactRegistry, BuildArtifact, ArtifactType, get_global_artifact_manager

__all__ = [
    'Builder',
    'Package',
    'MethodConfig',
    'BuildMethod',
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
    'GradleBuilder',
    'AndroidBuilder',
    'JavaBuilder',
    'MakefileBuilder',
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
    'select_builder',
    'get_builder_by_name',
    'get_available_builders',
    'validate_builder_compatibility',
    'select_builder_function',
    'BuildSession',
    'BuildSessionManager',
    'BuildStepResult',
    'BuildStatus',
    'should_continue_on_error',
    'get_resume_package',
    'ArtifactManager',
    'ArtifactRegistry',
    'BuildArtifact',
    'ArtifactType',
    'get_global_artifact_manager',
    'CrossCompilationConfig',
    'CrossCompilationHelper',
    'enhance_method_config_with_cross_compilation',
    'create_cross_compile_method'
]
