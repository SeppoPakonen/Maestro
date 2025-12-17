#!/usr/bin/env python3
"""
Test script to verify the unified build configuration system works with all existing builders.
"""

import tempfile
import shutil
from pathlib import Path

from maestro.builders import (
    MethodConfig,
    BuildType,
    OSFamily,
    MethodManager,
    GccBuilder,
    MsvcBuilder,
    CMakeBuilder,
    AutotoolsBuilder,
    MsBuildBuilder,
    MavenBuilder,
    UppBuilder,
    list_methods,
    create_default_methods
)
from maestro.builders.base import Package
from maestro.builders.host import LocalHost


def test_config_system():
    print("Testing unified build configuration system...")
    
    # Test 1: Method manager functionality
    print("\n1. Testing MethodManager...")
    manager = MethodManager()
    
    # Create default methods based on detected tools
    created_methods = create_default_methods()
    print(f"   Created {len(created_methods)} default methods: {created_methods}")
    
    # List available methods
    available_methods = list_methods()
    print(f"   Available methods: {available_methods}")
    
    # Test loading a method
    if available_methods:
        method_name = available_methods[0]
        method = manager.load_method(method_name)
        print(f"   Loaded method '{method_name}': builder={method.builder}")
    
    # Test 2: Configuration inheritance
    print("\n2. Testing configuration inheritance...")
    
    # Create a base config
    from maestro.builders.config import CompilerConfig, BuildConfig, PlatformConfig
    base_config = MethodConfig(
        name="base-config",
        builder="gcc",
        compiler=CompilerConfig(
            cc='gcc',
            cxx='g++',
            cflags=['-g', '-Wall'],
            cxxflags=['-g', '-Wall', '-std=c++17'],
            ldflags=['-g']
        ),
        config=BuildConfig(
            build_type=BuildType.DEBUG,
            parallel=True,
            jobs=4
        ),
        platform=PlatformConfig()
    )
    
    # Test 3: Test builder initialization with config
    print("\n3. Testing builders with configuration...")
    
    host = LocalHost()
    
    # Test GCC builder
    try:
        gcc_config = MethodConfig(
            name="gcc-test",
            builder="gcc",
            compiler=CompilerConfig(
                cc='gcc',
                cxx='g++',
                cflags=['-O2', '-DNDEBUG'],
                cxxflags=['-O2', '-DNDEBUG', '-std=c++17'],
                ldflags=[]
            ),
            config=BuildConfig(
                build_type=BuildType.RELEASE,
                parallel=True,
                jobs=4
            ),
            platform=PlatformConfig()
        )
        gcc_builder = GccBuilder(config=gcc_config)
        print(f"   GccBuilder initialized successfully with config: {gcc_builder.config.name}")
    except Exception as e:
        print(f"   GccBuilder failed: {e}")

    # Test MSVC builder
    try:
        msvc_config = MethodConfig(
            name="msvc-test",
            builder="msvc",
            compiler=CompilerConfig(),
            config=BuildConfig(),
            platform=PlatformConfig()
        )
        msvc_builder = MsvcBuilder(config=msvc_config)
        print(f"   MsvcBuilder initialized successfully with config: {msvc_builder.config.name}")
    except Exception as e:
        print(f"   MsvcBuilder failed: {e}")

    # Test CMake builder
    try:
        cmake_config = MethodConfig(
            name="cmake-test",
            builder="cmake",
            compiler=CompilerConfig(),
            config=BuildConfig(),
            platform=PlatformConfig()
        )
        cmake_builder = CMakeBuilder(config=cmake_config)
        print(f"   CMakeBuilder initialized successfully with config: {cmake_builder.config.name}")
    except Exception as e:
        print(f"   CMakeBuilder failed: {e}")

    # Test Autotools builder
    try:
        autotools_config = MethodConfig(
            name="autotools-test",
            builder="autotools",
            compiler=CompilerConfig(),
            config=BuildConfig(),
            platform=PlatformConfig()
        )
        autotools_builder = AutotoolsBuilder(config=autotools_config)
        print(f"   AutotoolsBuilder initialized successfully with config: {autotools_builder.config.name}")
    except Exception as e:
        print(f"   AutotoolsBuilder failed: {e}")

    # Test MSBuild builder
    try:
        msbuild_config = MethodConfig(
            name="msbuild-test",
            builder="msbuild",
            compiler=CompilerConfig(),
            config=BuildConfig(),
            platform=PlatformConfig()
        )
        msbuild_builder = MsBuildBuilder(config=msbuild_config)
        print(f"   MsBuildBuilder initialized successfully with config: {msbuild_builder.config.name}")
    except Exception as e:
        print(f"   MsBuildBuilder failed: {e}")

    # Test Maven builder
    try:
        maven_config = MethodConfig(
            name="maven-test",
            builder="maven",
            compiler=CompilerConfig(),
            config=BuildConfig(),
            platform=PlatformConfig()
        )
        maven_builder = MavenBuilder(config=maven_config)
        print(f"   MavenBuilder initialized successfully with config: {maven_builder.config.name}")
    except Exception as e:
        print(f"   MavenBuilder failed: {e}")

    # Test UppBuilder
    try:
        upp_config = MethodConfig(
            name="upp-test",
            builder="upp",
            compiler=CompilerConfig(),
            config=BuildConfig(),
            platform=PlatformConfig()
        )
        upp_builder = UppBuilder(host=host, config=upp_config)
        print(f"   UppBuilder initialized successfully with config: {upp_builder.config.name}")
    except Exception as e:
        print(f"   UppBuilder failed: {e}")
    
    # Test 4: Per-package configuration
    print("\n4. Testing per-package configuration...")
    from maestro.builders.config import get_package_method_override, set_package_method_override

    # Create a test package config
    test_pkg_config = MethodConfig(
        name="test-pkg-config",
        builder="gcc",
        compiler=CompilerConfig(
            cxxflags=['-DTEST_PACKAGE']
        ),
        config=BuildConfig(),
        platform=PlatformConfig()
    )

    set_package_method_override("test_package", test_pkg_config)
    retrieved_config = get_package_method_override("test_package")
    print(f"   Per-package config set and retrieved: {retrieved_config.name if retrieved_config else 'None'}")
    
    print("\nAll tests completed!")


def test_builder_methods():
    """Test that all builders can be instantiated with the new configuration system."""
    print("\nTesting builder instantiation with new config system...")

    host = LocalHost()

    # Create a basic config
    from maestro.builders.config import CompilerConfig, BuildConfig, PlatformConfig
    basic_config = MethodConfig(
        name="basic-config",
        builder="gcc",
        compiler=CompilerConfig(),
        config=BuildConfig(),
        platform=PlatformConfig()
    )

    builders_and_configs = [
        (GccBuilder, {}),
        (MsvcBuilder, {}),
        (CMakeBuilder, {}),
        (AutotoolsBuilder, {}),
        (MsBuildBuilder, {}),
        (MavenBuilder, {}),
        (UppBuilder, {"host": host})
    ]

    for BuilderClass, extra_kwargs in builders_and_configs:
        try:
            # Try to initialize with config
            builder = BuilderClass(config=basic_config, **extra_kwargs)
            print(f"   {BuilderClass.__name__}: OK - config={builder.config.name}")
        except Exception as e:
            print(f"   {BuilderClass.__name__}: FAILED - {e}")


if __name__ == "__main__":
    test_config_system()
    test_builder_methods()