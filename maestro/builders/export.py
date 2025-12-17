"""
Project export functionality for Maestro.

Implements export of packages to various build system formats:
- Makefile (GNU Make)
- CMakeLists.txt (CMake)
- Visual Studio project files
- Ninja build files
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from ..repo.package import PackageInfo


@dataclass
class ExportConfig:
    """Configuration for project export."""
    format: str  # Target format: makefile, cmake, msbuild, ninja
    output_dir: str  # Output directory
    project_name: str  # Project name for exported project
    include_dependencies: bool = True  # Whether to include dependencies
    include_resources: bool = True  # Whether to include resource files
    make_target: str = "all"  # Make target name (for Makefile export)
    cmake_version: str = "3.10"  # CMake minimum required version
    vs_platform: str = "x64"  # Visual Studio platform


class Exporter:
    """Base exporter class."""
    
    def __init__(self, config: ExportConfig):
        self.config = config
    
    def export(self, package: PackageInfo) -> bool:
        """
        Export a package to the target format.
        
        Args:
            package: Package information to export
            
        Returns:
            True if export was successful, False otherwise
        """
        if self.config.format == "makefile":
            return self.export_makefile(package)
        elif self.config.format == "cmake":
            return self.export_cmake(package)
        elif self.config.format == "msbuild":
            return self.export_msbuild(package)
        elif self.config.format == "ninja":
            return self.export_ninja(package)
        else:
            raise ValueError(f"Unsupported export format: {self.config.format}")
    
    def export_makefile(self, package: PackageInfo) -> bool:
        """
        Export package to GNU Makefile format.
        
        Args:
            package: Package information to export
            
        Returns:
            True if export was successful, False otherwise
        """
        # Get all source files from the package
        source_files = self._get_source_files(package)
        
        # Separate C++ and C files
        cpp_files = [f for f in source_files if f.endswith(('.cpp', '.cc', '.cxx', '.C'))]
        c_files = [f for f in source_files if f.endswith('.c')]
        
        # Generate object file names
        obj_files_cpp = [f.replace('.cpp', '.o').replace('.cc', '.o').replace('.cxx', '.o').replace('.C', '.o') for f in cpp_files]
        obj_files_c = [f.replace('.c', '.o') for f in c_files]
        all_obj_files = obj_files_cpp + obj_files_c
        
        # Get include directories
        include_dirs = self._get_include_dirs(package)
        include_flags = ' '.join([f'-I{d}' for d in include_dirs])
        
        # Generate Makefile content
        makefile_content = f"""# Generated Makefile for {package.name}
# Exported by Maestro

# Compiler settings
CXX = g++
CC = gcc
CXXFLAGS = -std=c++17 {include_flags} -O2 -Wall
CFLAGS = {include_flags} -O2 -Wall
LDFLAGS = 
LIBS = 

# Source and object files
CPP_SOURCES = {' '.join(cpp_files)}
C_SOURCES = {' '.join(c_files)}
OBJECTS = {' '.join(all_obj_files)}

# Target executable name
TARGET = {self.config.project_name or package.name}

# Default target
.PHONY: all clean

all: $(TARGET)

# Link executable
$(TARGET): $(OBJECTS)
\t$(CXX) $(OBJECTS) -o $(TARGET) $(LDFLAGS) $(LIBS)

# Compile C++ files
"""
        for cpp_src, obj_file in zip(cpp_files, obj_files_cpp):
            makefile_content += f"{obj_file}: {cpp_src}\n"
            makefile_content += f"\t$(CXX) $(CXXFLAGS) -c {cpp_src} -o {obj_file}\n\n"
        
        for c_src, obj_file in zip(c_files, obj_files_c):
            makefile_content += f"{obj_file}: {c_src}\n"
            makefile_content += f"\t$(CC) $(CFLAGS) -c {c_src} -o {obj_file}\n\n"
        
        makefile_content += f"""# Clean build artifacts
clean:
\trm -f $(OBJECTS) $(TARGET)

# Install target (if needed)
install: $(TARGET)
\tinstall -m 755 $(TARGET) /usr/local/bin/
"""
        
        # Write Makefile to output directory
        output_path = os.path.join(self.config.output_dir, "Makefile")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(makefile_content)
        
        print(f"Makefile exported to: {output_path}")
        return True
    
    def export_cmake(self, package: PackageInfo) -> bool:
        """
        Export package to CMakeLists.txt format.
        
        Args:
            package: Package information to export
            
        Returns:
            True if export was successful, False otherwise
        """
        # Get all source files from the package
        source_files = self._get_source_files(package)
        
        # Separate header and source files
        header_files = [f for f in source_files if f.endswith(('.h', '.hpp', '.hxx', '.hh'))]
        source_files_only = [f for f in source_files if f not in header_files]
        
        # Get dependencies
        dependencies = package.uses if hasattr(package, 'uses') else []
        
        # Generate CMakeLists.txt content
        cmake_content = f"""# Generated CMakeLists.txt for {package.name}
# Exported by Maestro

cmake_minimum_required(VERSION {self.config.cmake_version})
project({self.config.project_name or package.name})

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Source files
set(SOURCES
"""
        for src in source_files_only:
            cmake_content += f"    {src}\n"
        cmake_content += f""")
        
# Header files (for IDEs)
set(HEADERS
"""
        for header in header_files:
            cmake_content += f"    {header}\n"
        cmake_content += f""")
        
# Include directories
include_directories(
"""
        include_dirs = self._get_include_dirs(package)
        for inc_dir in include_dirs:
            cmake_content += f"    {inc_dir}\n"
        cmake_content += f""")
        
# Add executable
add_executable(${{PROJECT_NAME}}
    ${{SOURCES}}
    ${{HEADERS}}
)

# Link libraries if any dependencies exist
"""
        # Add link libraries for dependencies if they exist
        for dep in dependencies:
            if dep.lower().startswith('lib'):
                lib_name = dep[3:]  # Remove 'lib' prefix
            else:
                lib_name = dep
            cmake_content += f"target_link_libraries(${{PROJECT_NAME}} {lib_name})\n"
        
        # Write CMakeLists.txt to output directory
        output_path = os.path.join(self.config.output_dir, "CMakeLists.txt")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(cmake_content)
        
        print(f"CMakeLists.txt exported to: {output_path}")
        return True
    
    def export_msbuild(self, package: PackageInfo) -> bool:
        """
        Export package to Visual Studio MSBuild format (.vcxproj).
        
        Args:
            package: Package information to export
            
        Returns:
            True if export was successful, False otherwise
        """
        # Get all source files from the package
        source_files = self._get_source_files(package)
        
        # Separate different file types
        cpp_files = [f for f in source_files if f.endswith(('.cpp', '.cc', '.cxx'))]
        header_files = [f for f in source_files if f.endswith(('.h', '.hpp', '.hxx', '.hh'))]
        
        # Generate MSBuild project content
        msbuild_content = f"""<?xml version="1.0" encoding="utf-8"?>
<Project DefaultTargets="Build" xmlns="http://schemas.microsoft.com/developer/msbuild/2003">
  <ItemGroup Label="ProjectConfigurations">
    <ProjectConfiguration Include="Debug|{self.config.vs_platform}">
      <Configuration>Debug</Configuration>
      <Platform>{self.config.vs_platform}</Platform>
    </ProjectConfiguration>
    <ProjectConfiguration Include="Release|{self.config.vs_platform}">
      <Configuration>Release</Configuration>
      <Platform>{self.config.vs_platform}</Platform>
    </ProjectConfiguration>
  </ItemGroup>
  <PropertyGroup Label="Globals">
    <VCProjectVersion>16.0</VCProjectVersion>
    <Keyword>Win32Proj</Keyword>
    <ProjectGuid>{{"""
        
        # Generate a project GUID (simplified)
        import uuid
        project_guid = str(uuid.uuid4()).upper()
        msbuild_content += f"{project_guid}}}\n"
        msbuild_content += f"""    <RootNamespace>{self.config.project_name or package.name}</RootNamespace>
    <WindowsTargetPlatformVersion>10.0</WindowsTargetPlatformVersion>
  </PropertyGroup>
  <Import Project="$(VCTargetsPath)\\Microsoft.Cpp.Default.props" />
  <PropertyGroup Condition="'$(Configuration)|$(Platform)'=='Debug|{self.config.vs_platform}'" Label="Configuration">
    <ConfigurationType>Application</ConfigurationType>
    <UseDebugLibraries>true</UseDebugLibraries>
    <PlatformToolset>v143</PlatformToolset>
    <CharacterSet>Unicode</CharacterSet>
  </PropertyGroup>
  <PropertyGroup Condition="'$(Configuration)|$(Platform)'=='Release|{self.config.vs_platform}'" Label="Configuration">
    <ConfigurationType>Application</ConfigurationType>
    <UseDebugLibraries>false</UseDebugLibraries>
    <PlatformToolset>v143</PlatformToolset>
    <WholeProgramOptimization>true</WholeProgramOptimization>
    <CharacterSet>Unicode</CharacterSet>
  </PropertyGroup>
  <Import Project="$(VCTargetsPath)\\Microsoft.Cpp.props" />
  <ImportGroup Label="ExtensionSettings">
  </ImportGroup>
  <ImportGroup Label="Shared">
  </ImportGroup>
  <ImportGroup Label="PropertySheets" Condition="'$(Configuration)|$(Platform)'=='Debug|{self.config.vs_platform}'">
    <Import Project="$(UserRootDir)\\Microsoft.Cpp.$(Platform).user.props" Condition="exists('$(UserRootDir)\\Microsoft.Cpp.$(Platform).user.props')" Label="LocalAppDataPlatform" />
  </ImportGroup>
  <ImportGroup Label="PropertySheets" Condition="'$(Configuration)|$(Platform)'=='Release|{self.config.vs_platform}'">
    <Import Project="$(UserRootDir)\\Microsoft.Cpp.$(Platform).user.props" Condition="exists('$(UserRootDir)\\Microsoft.Cpp.$(Platform).user.props')" Label="LocalAppDataPlatform" />
  </ImportGroup>
  <PropertyGroup Label="UserMacros" />
  <PropertyGroup Condition="'$(Configuration)|$(Platform)'=='Debug|{self.config.vs_platform}'">
    <LinkIncremental>true</LinkIncremental>
  </PropertyGroup>
  <PropertyGroup Condition="'$(Configuration)|$(Platform)'=='Release|{self.config.vs_platform}'">
    <LinkIncremental>false</LinkIncremental>
  </PropertyGroup>
  <ItemDefinitionGroup Condition="'$(Configuration)|$(Platform)'=='Debug|{self.config.vs_platform}'">
    <ClCompile>
      <WarningLevel>Level3</WarningLevel>
      <SDLCheck>true</SDLCheck>
      <PreprocessorDefinitions>_DEBUG;_CONSOLE;%(PreprocessorDefinitions)</PreprocessorDefinitions>
      <ConformanceMode>true</ConformanceMode>
"""
        
        # Add include directories
        include_dirs = self._get_include_dirs(package)
        if include_dirs:
            msbuild_content += "      <AdditionalIncludeDirectories>"
            msbuild_content += ";".join(include_dirs)
            msbuild_content += ";%(AdditionalIncludeDirectories)</AdditionalIncludeDirectories>\n"
        
        msbuild_content += f"""    </ClCompile>
    <Link>
      <SubSystem>Console</SubSystem>
      <GenerateDebugInformation>true</GenerateDebugInformation>
    </Link>
  </ItemDefinitionGroup>
  <ItemDefinitionGroup Condition="'$(Configuration)|$(Platform)'=='Release|{self.config.vs_platform}'">
    <ClCompile>
      <WarningLevel>Level3</WarningLevel>
      <FunctionLevelLinking>true</FunctionLevelLinking>
      <IntrinsicFunctions>true</IntrinsicFunctions>
      <SDLCheck>true</SDLCheck>
      <PreprocessorDefinitions>NDEBUG;_CONSOLE;%(PreprocessorDefinitions)</PreprocessorDefinitions>
      <ConformanceMode>true</ConformanceMode>
"""
        if include_dirs:
            msbuild_content += "      <AdditionalIncludeDirectories>"
            msbuild_content += ";".join(include_dirs)
            msbuild_content += ";%(AdditionalIncludeDirectories)</AdditionalIncludeDirectories>\n"
        
        msbuild_content += f"""    </ClCompile>
    <Link>
      <SubSystem>Console</SubSystem>
      <EnableCOMDATFolding>true</EnableCOMDATFolding>
      <OptimizeReferences>true</OptimizeReferences>
      <GenerateDebugInformation>true</GenerateDebugInformation>
    </Link>
  </ItemDefinitionGroup>
"""
        
        # Add source files
        if cpp_files:
            msbuild_content += "  <ItemGroup>\n"
            for cpp_file in cpp_files:
                msbuild_content += f"    <ClCompile Include=\"{cpp_file}\" />\n"
            msbuild_content += "  </ItemGroup>\n"
        
        # Add header files
        if header_files:
            msbuild_content += "  <ItemGroup>\n"
            for header_file in header_files:
                msbuild_content += f"    <ClInclude Include=\"{header_file}\" />\n"
            msbuild_content += "  </ItemGroup>\n"
        
        msbuild_content += f"""  <Import Project="$(VCTargetsPath)\\Microsoft.Cpp.targets" />
  <ImportGroup Label="ExtensionTargets">
  </ImportGroup>
</Project>
"""
        
        # Write .vcxproj file to output directory
        project_name = self.config.project_name or package.name
        output_path = os.path.join(self.config.output_dir, f"{project_name}.vcxproj")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(msbuild_content)
        
        print(f"Visual Studio project exported to: {output_path}")
        return True
    
    def export_ninja(self, package: PackageInfo) -> bool:
        """
        Export package to Ninja build file format.
        
        Args:
            package: Package information to export
            
        Returns:
            True if export was successful, False otherwise
        """
        # Get all source files from the package
        source_files = self._get_source_files(package)
        
        # Separate C++ and C files
        cpp_files = [f for f in source_files if f.endswith(('.cpp', '.cc', '.cxx', '.C'))]
        c_files = [f for f in source_files if f.endswith('.c')]
        
        # Generate object file names
        obj_files_cpp = [f.replace('.cpp', '.o').replace('.cc', '.o').replace('.cxx', '.o').replace('.C', '.o') for f in cpp_files]
        obj_files_c = [f.replace('.c', '.o') for f in c_files]
        all_obj_files = obj_files_cpp + obj_files_c
        
        # Get include directories
        include_dirs = self._get_include_dirs(package)
        include_flags = ' '.join([f'-I{d}' for d in include_dirs])
        
        # Generate Ninja build file content
        ninja_content = f"""# Generated ninja build file for {package.name}
# Exported by Maestro

# Variables
cflags = -O2 -Wall {include_flags}
cxxflags = -std=c++17 -O2 -Wall {include_flags}
ldflags = 
libs = 

# Rules
rule cc
  command = gcc $cflags -c $in -o $out
  description = CC $out
  generator = 1

rule cxx
  command = g++ $cxxflags -c $in -o $out
  description = CXX $out
  generator = 1

rule link
  command = g++ $ldflags $in -o $out $libs
  description = LINK $out
  generator = 1

# Build statements
"""
        
        # Build statements for C++ files
        for cpp_src, obj_file in zip(cpp_files, obj_files_cpp):
            ninja_content += f"build {obj_file}: cxx {cpp_src}\n"
        
        # Build statements for C files
        for c_src, obj_file in zip(c_files, obj_files_c):
            ninja_content += f"build {obj_file}: cc {c_src}\n"
        
        # Link all objects to target
        target_name = self.config.project_name or package.name
        ninja_content += f"\nbuild {target_name}: link {' '.join(all_obj_files)}\n\n"
        
        # Default target
        ninja_content += "default {}\n".format(target_name)
        
        # Write build.ninja file to output directory
        output_path = os.path.join(self.config.output_dir, "build.ninja")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(ninja_content)
        
        print(f"Ninja build file exported to: {output_path}")
        return True
    
    def _get_source_files(self, package: PackageInfo) -> List[str]:
        """Get all source files from a package."""
        # This is a simplified implementation
        # In a real implementation, this would parse the package metadata to get source files
        source_extensions = [
            '.cpp', '.cc', '.cxx', '.c', '.C',  # C/C++
            '.java',  # Java
            '.py',    # Python
            '.js',    # JavaScript
            '.ts',    # TypeScript
            # Add more as needed
        ]
        
        source_files = []
        
        # Walk through the package directory
        for root, dirs, files in os.walk(package.dir):
            for file in files:
                if any(file.lower().endswith(ext) for ext in source_extensions):
                    # Get relative path from package directory
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, package.dir)
                    source_files.append(rel_path)
        
        return source_files
    
    def _get_include_dirs(self, package: PackageInfo) -> List[str]:
        """Get include directories for a package."""
        # This is a simplified implementation
        # In a real implementation, this would analyze package dependencies
        # and include directories from build metadata
        include_dirs = [package.dir]  # Include the package directory itself
        
        # Add subdirectories that might contain headers
        for root, dirs, files in os.walk(package.dir):
            for dir_name in dirs:
                if dir_name.lower() in ['include', 'inc', 'headers']:
                    include_path = os.path.join(root, dir_name)
                    rel_path = os.path.relpath(include_path, package.dir)
                    include_dirs.append(rel_path)
        
        return include_dirs


class MakeFileExporter(Exporter):
    """Specific exporter for Makefile format."""
    
    def __init__(self, output_dir: str, project_name: str = None):
        config = ExportConfig(
            format="makefile",
            output_dir=output_dir,
            project_name=project_name or "project"
        )
        super().__init__(config)


class CMakeExporter(Exporter):
    """Specific exporter for CMake format."""
    
    def __init__(self, output_dir: str, project_name: str = None):
        config = ExportConfig(
            format="cmake",
            output_dir=output_dir,
            project_name=project_name or "project"
        )
        super().__init__(config)


class MSBuildExporter(Exporter):
    """Specific exporter for MSBuild format."""
    
    def __init__(self, output_dir: str, project_name: str = None, platform: str = "x64"):
        config = ExportConfig(
            format="msbuild",
            output_dir=output_dir,
            project_name=project_name or "project",
            vs_platform=platform
        )
        super().__init__(config)


class NinjaExporter(Exporter):
    """Specific exporter for Ninja format."""
    
    def __init__(self, output_dir: str, project_name: str = None):
        config = ExportConfig(
            format="ninja",
            output_dir=output_dir,
            project_name=project_name or "project"
        )
        super().__init__(config)


def export_package_to_format(package: PackageInfo, export_format: str, output_dir: str, project_name: str = None) -> bool:
    """
    Helper function to export a package to a specific format.
    
    Args:
        package: Package information to export
        export_format: Format to export to (makefile, cmake, msbuild, ninja)
        output_dir: Directory to export to
        project_name: Name for the exported project
        
    Returns:
        True if export was successful, False otherwise
    """
    config = ExportConfig(
        format=export_format,
        output_dir=output_dir,
        project_name=project_name or package.name
    )
    
    exporter = Exporter(config)
    return exporter.export(package)