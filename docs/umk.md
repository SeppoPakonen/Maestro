# UMK Integration Roadmap

## Executive Summary

This document outlines the integration plan for **umk** (U++ make) build system into Maestro, creating a universal build orchestration system that extends beyond U++ to support CMake, Autotools, Maven, and Visual Studio projects.

**Vision**: `maestro make` becomes a universal build command that can build any package detected by `maestro repo resolve`, regardless of the underlying build system (U++, CMake, Autotools, Maven, Visual Studio, Make).

## Source Code Locations

### U++ umk Sources
- **Core umk**: `/home/sblo/upp/uppsrc/umk/`
  - `umake.h` - Main header with Console and Ide classes
  - `umk.cpp` - Entry point (Windows launcher)
  - `umake.cpp` - Main build logic implementation
  - `MakeBuild.cpp` - Build orchestration
  - `Console.cpp` - Console output and process management
  - `Export.cpp` - Project export functionality
  - `IdeContext.cpp` - IDE integration interface
  - `UppHub.cpp` - Package hub integration

- **Builder Infrastructure**: `/home/sblo/upp/uppsrc/ide/Builders/`
  - `Builders.h` - Builder interface definitions
  - `Build.h` - Build configuration and TargetMode
  - `GccBuilder.cpp` - GCC/Clang builder implementation
  - `MscBuilder.cpp` - MSVC builder implementation
  - `JavaBuilder.cpp` - Java builder
  - `ScriptBuilder.cpp` - Script-based builds
  - `AndroidBuilder.h/cpp` - Android NDK builds
  - `MakeFile.cpp` - Makefile generation
  - `Blitz.cpp` - Blitz build (unity build) support
  - `CCJ.cpp` - compile_commands.json generation
  - `BuilderUtils.h/cpp` - Shared builder utilities

- **Core Infrastructure**: `/home/sblo/upp/uppsrc/ide/Core/`
  - `Core.h` - Core definitions, IdeContext, Workspace, Package
  - `Builder.cpp` - Base builder implementation
  - `Package.cpp` - Package file parsing (.upp format)
  - `Workspace.cpp` - Workspace scanning and dependency resolution
  - `PPinfo.cpp` - Preprocessor dependency tracking
  - `Assembly.cpp` - Assembly (nest) management
  - `Host.h/cpp` - Host platform abstraction
  - `Cache.cpp` - Build cache management
  - `BinObj.cpp` - Binary object embedding (.brc files)

- **Android Support**: `/home/sblo/upp/uppsrc/ide/Android/`
  - `Android.h/cpp` - Android build system integration
  - `AndroidSDK.cpp` - SDK management
  - `AndroidNDK.cpp` - NDK integration
  - `Apk.cpp` - APK packaging
  - `AndroidManifest.cpp` - Manifest generation

- **Java Support**: `/home/sblo/upp/uppsrc/ide/Java/`
  - `Java.h/cpp` - Java integration
  - `Jdk.cpp` - JDK detection and management

## Architecture Overview

### Current State (Maestro v1.2.1)

```
maestro repo resolve  → Scans for packages (U++, CMake, Autotools, Maven, MSVS)
                      → Outputs .maestro/repo/index.json
                      → Outputs .maestro/repo/state.json

maestro repo show     → Shows scan summary

maestro repo pkg      → Query packages (list, info, search, tree)
```

### Target State (Maestro with umk Integration)

```
maestro repo resolve  → [unchanged] Scans packages

maestro make          → Universal build orchestration
├── build             → Build package(s)
├── clean             → Clean build artifacts
├── rebuild           → Clean + build
├── export            → Export project (makefile, CMakeLists.txt, .vcxproj)
├── config            → Configure build method
└── methods           → List available build methods
```

## Key Concepts from umk

### 1. Build Methods
U++ uses "build methods" which are build toolchain configurations stored in `~/.upp/` directory or nest-specific locations. Each method defines:
- Compiler paths and flags
- Linker options
- Platform-specific settings
- Debug/Release configurations

**Example methods**: GCC, CLANG, MSC9ARM, MSC71, ANDROID, etc.

### 2. Builder Pattern
The Builder base class provides virtual interface:
```cpp
struct Builder {
    virtual bool BuildPackage(...) = 0;
    virtual bool Link(...) = 0;
    virtual bool Preprocess(...) = 0;
    virtual void CleanPackage(...) = 0;
    virtual String GetTargetExt() const = 0;
};
```

Concrete implementations:
- `GccBuilder` - GCC/Clang for Linux/macOS/MinGW
- `MscBuilder` - MSVC for Windows
- `JavaBuilder` - Java/JAR builds
- `AndroidBuilder` - Android NDK/APK builds
- `ScriptBuilder` - Custom script-based builds

### 3. Package Structure (.upp files)
U++ packages use `.upp` descriptor files with format:
```
description "Package description";

uses
    Core,
    plugin/z;

file
    main.cpp,
    utils.cpp,
    utils.h;

mainconfig
    "" = "GUI MT";
```

### 4. Workspace Dependency Resolution
The `Workspace` class scans packages recursively based on `uses` declarations, building a complete dependency graph.

### 5. Blitz Build (Unity Build)
U++ supports "blitz" mode where multiple `.cpp` files are concatenated into a single translation unit for faster compilation.

### 6. Preprocessor Dependency Tracking
`PPInfo` class provides sophisticated header dependency tracking with:
- Include file resolution
- Macro/define tracking
- Conditional include handling (`#if flagXXX`)
- Cache for faster incremental builds

### 7. Console Process Management
The `Console` class provides parallel build job management:
- Multi-slot parallel execution
- Process output capture and streaming
- Error tracking and reporting
- Build groups for organizing output

### 8. Android Builder System
The `AndroidBuilder` provides comprehensive Android application building:

**Key components**:
- **AndroidSDK**: SDK management and validation
  - Platform detection (android-XX)
  - Build tools version management
  - Tool paths: aapt, d8/dx, apksigner, zipalign, adb
  - Device and emulator detection
- **AndroidNDK**: Native Development Kit integration
  - Platform selection (arm, arm64, x86, x86_64)
  - Toolchain management
  - C++ runtime selection (c++_static, c++_shared)
  - ndk-build integration
- **APK packaging**: Complete APK generation pipeline
  - Resource compilation (aapt)
  - DEX generation (d8 or dx)
  - APK assembly and alignment (zipalign)
  - APK signing (apksigner or jarsigner)
- **AndroidManifest**: Manifest generation and parsing
  - Package name, version, permissions
  - MinSdkVersion, TargetSdkVersion
  - Activities, services, receivers
- **Multi-architecture builds**: Build for multiple CPU architectures
  - armeabi-v7a (32-bit ARM)
  - arm64-v8a (64-bit ARM)
  - x86 (32-bit Intel)
  - x86_64 (64-bit Intel)
- **JNI support**: Java Native Interface integration
  - C++ code compiled to native libraries (.so)
  - Java code compiled to DEX
  - Automatic JNI header generation

**Build process**:
1. Compile Java sources (javac)
2. Generate R.java from resources (aapt)
3. Compile native code (ndk-build or direct gcc/clang)
4. Package resources into APK (aapt)
5. Convert .class to .dex (d8/dx)
6. Add native libraries to APK
7. Align APK (zipalign)
8. Sign APK (apksigner)

**U++ Android features**:
- Automatic project structure generation
- Android.mk generation for NDK
- Blitz build support for C++ code
- Resource package flag (ANDROID_RESOURCES_PACKAGE)
- Mixed Java/C++ packages

### 9. Java Builder System
The `JavaBuilder` provides Java/JAR building:

**Key components**:
- **JDK detection**: Automatic JDK discovery and validation
  - Version detection (Java 8, 11, 17, etc.)
  - Tool paths: javac, jar, javadoc, javah, jarsigner
- **Compilation**: Java source compilation
  - Classpath management
  - Debug vs Release builds (-g flag)
  - Custom javac options
- **JAR packaging**: Create executable and library JARs
  - Manifest.mf generation
  - Main-Class specification
  - Classpath in manifest
- **Preprocessing**: Line ending normalization
  - Convert # directives to //
  - Path normalization
- **Incremental builds**: Timestamp-based recompilation

**Build process**:
1. Preprocess .java files (line ending fixes)
2. Compile to .class files (javac)
3. Package into .jar (jar)
4. Optional: Sign JAR (jarsigner)

**Use cases**:
- Pure Java applications
- Java libraries for Android
- JNI header generation for C++ integration

### 10. Universal Hub System (MaestroHub)
Inspired by UppHub but generalized for all build systems, providing automatic package/repository discovery and installation:

**Key concepts**:
- **Hub metadata**: JSON-based registry of repositories
  - Repository name and description
  - Git URL and branch
  - Package list
  - Category (libraries, tools, games, etc.)
  - Status (stable, beta, experimental)
  - Website/documentation links
- **Hub hierarchy**: Tiered system with links
  - Primary hub: Official Maestro package registry
  - Secondary hubs: Community, organization-specific
  - Tertiary hubs: Personal, experimental
- **Auto-discovery**: Automatic dependency resolution
  - Scan project for missing packages
  - Search hub registries for matches
  - Auto-clone repositories
  - Recursive dependency installation
- **Multi-ecosystem support**: Universal across build systems
  - U++ packages from UppHub
  - CMake projects from GitHub/GitLab
  - Conan/vcpkg integration
  - npm/pip/cargo bridge support

**Hub structure** (`nests.json` format):
```json
{
  "name": "MaestroHub-Main",
  "description": "Official Maestro package hub",
  "nests": [
    {
      "name": "ai-upp",
      "description": "AI fork of Ultimate++ framework",
      "repository": "https://github.com/user/ai-upp.git",
      "branch": "main",
      "packages": ["Core", "Draw", "Painter", "..."],
      "category": "framework",
      "status": "stable",
      "website": "https://github.com/user/ai-upp",
      "readme": "https://raw.githubusercontent.com/user/ai-upp/main/README.md",
      "build_system": "upp"
    },
    {
      "name": "my-cmake-libs",
      "description": "Collection of CMake-based libraries",
      "repository": "https://github.com/user/cmake-libs.git",
      "packages": ["libfoo", "libbar"],
      "category": "libraries",
      "status": "stable",
      "build_system": "cmake"
    }
  ],
  "links": [
    "https://raw.githubusercontent.com/community/maestro-hub-community/main/nests.json"
  ]
}
```

**Storage structure**:
```
~/.maestro/
├── config.toml              # Global Maestro configuration
├── methods/                 # Build methods
├── cache/                   # Global build cache
└── hub/                     # Hub repositories
    ├── ai-upp/              # Cloned hub repository
    │   ├── uppsrc/
    │   └── .git/
    ├── my-cmake-libs/
    │   ├── libfoo/
    │   ├── libbar/
    │   └── .git/
    └── .hub-cache.json      # Hub metadata cache
```

**Hub operations**:
1. **Load**: Fetch and parse hub metadata JSON
2. **Search**: Find packages across registered hubs
3. **Install**: Clone repository and install packages
4. **Update**: Pull latest changes from repositories
5. **Auto-resolve**: Automatically install missing dependencies

**Workflow example**:
```bash
# User tries to build project with missing dependency
$ maestro make build MyProject

# Maestro detects missing package "libfoo"
[maestro] Missing package: libfoo
[maestro] Searching MaestroHub...
[maestro] Found libfoo in nest 'my-cmake-libs'
[maestro] Clone https://github.com/user/cmake-libs.git? [Y/n] y
[maestro] Cloning to ~/.maestro/hub/my-cmake-libs...
[maestro] Scanning dependencies of libfoo...
[maestro] All dependencies satisfied
[maestro] Building libfoo...
[maestro] Building MyProject...
```

**Integration with existing systems**:
- **U++ UppHub**: Direct compatibility with existing UppHub JSON format
- **Conan**: Bridge to Conan package manager for C++ libraries
- **vcpkg**: Integration with Microsoft's vcpkg
- **CMake FetchContent**: Generate CMakeLists.txt with FetchContent
- **Git submodules**: Option to use git submodules instead of hub clones

## Integration Strategy

### Phase 1: Core Builder Abstraction (Python)

**Goal**: Create Python abstraction layer that wraps U++ Builder concepts.

**Tasks**:
1. Create `maestro/builders/` module structure:
   ```
   maestro/builders/
   ├── __init__.py
   ├── base.py          # Abstract Builder base class
   ├── gcc.py           # GCC/Clang builder
   ├── msvc.py          # MSVC builder
   ├── cmake.py         # CMake builder (new)
   ├── autotools.py     # Autotools builder (new)
   ├── msbuild.py       # MSBuild builder (new)
   ├── maven.py         # Maven builder (new)
   ├── android.py       # Android builder (NDK + SDK)
   ├── java.py          # Java/JAR builder
   ├── host.py          # Host abstraction (local, remote, docker)
   ├── console.py       # Process management and parallel execution
   └── config.py        # Build method configuration
   ```

2. Design Python `Builder` base class:
   ```python
   class Builder(ABC):
       @abstractmethod
       def build_package(self, package, config):
           """Build a single package."""
           pass

       @abstractmethod
       def link(self, linkfiles, linkoptions):
           """Link final executable/library."""
           pass

       @abstractmethod
       def clean_package(self, package):
           """Clean package build artifacts."""
           pass

       @abstractmethod
       def get_target_ext(self):
           """Return target file extension (.exe, .so, .a, etc)."""
           pass
   ```

3. Implement build method configuration:
   - Store in `.maestro/methods/` directory
   - Support TOML/JSON format for method definitions
   - Auto-detect system compilers
   - Support user overrides

**Deliverables**:
- Python builder framework with abstract base class
- Build method configuration system
- Host abstraction for local/remote builds

**Estimated Complexity**: Medium (2-3 weeks)

### Phase 2: U++ Builder Implementation

**Goal**: Implement native U++ package building using umk logic ported to Python.

**Tasks**:
1. Port U++ package parser:
   - Parse `.upp` files (already partially done in repo scanner)
   - Extract uses, files, flags, mainconfig
   - Resolve conditional options based on build flags

2. Implement workspace dependency resolver:
   - Port `Workspace::Scan()` logic
   - Build dependency graph
   - Determine build order
   - Handle circular dependency detection

3. Port GccBuilder logic:
   - Command-line construction with includes, defines, flags
   - Source file compilation with dependency tracking
   - Object file generation
   - Linking (executable, shared library, static library)
   - PCH (precompiled header) support
   - Blitz build support

4. Implement incremental build:
   - Port `PPInfo` dependency tracking
   - File timestamp comparison
   - Build cache in `.maestro/cache/`
   - Parallel compilation using Python multiprocessing

5. Port Console process management:
   - Multi-job parallel execution
   - Output streaming and capture
   - Error detection and reporting
   - Ctrl+C handling and process cleanup

**Deliverables**:
- Complete U++ builder that can build existing U++ projects
- Support for all mainconfig options
- Parallel build support
- Incremental build with dependency tracking

**Estimated Complexity**: High (4-6 weeks)

### Phase 3: CMake Builder

**Goal**: Build CMake-based packages detected by `maestro repo resolve`.

**Tasks**:
1. Implement CMake builder:
   ```python
   class CMakeBuilder(Builder):
       def configure(self, package, config):
           """Run cmake configuration."""
           cmake_args = [
               'cmake',
               '-S', package.dir,
               '-B', build_dir,
               f'-DCMAKE_BUILD_TYPE={config.build_type}',
               f'-DCMAKE_INSTALL_PREFIX={config.install_prefix}',
           ]
           # Add toolchain file if cross-compiling
           # Add custom flags from build method

       def build_package(self, package, config):
           """Build using cmake --build."""
           cmake_args = ['cmake', '--build', build_dir]
           if config.parallel:
               cmake_args.extend(['-j', str(config.jobs)])
   ```

2. Map Maestro build config to CMake:
   - Build type: Debug/Release → CMAKE_BUILD_TYPE
   - Compiler: GCC/Clang/MSVC → CMAKE_C_COMPILER/CMAKE_CXX_COMPILER
   - Platform flags → Toolchain file
   - Custom flags → CMAKE_CXX_FLAGS

3. Support CMake targets:
   - Build specific targets
   - Install support
   - Package generation (CPack)

4. Handle CMake variants:
   - Single-config generators (Makefiles, Ninja)
   - Multi-config generators (Visual Studio, Xcode)
   - Cross-compilation with toolchain files

**Deliverables**:
- CMake builder that can build CMake packages
- Support for custom CMake options
- Integration with CMake presets (CMakePresets.json)

**Estimated Complexity**: Medium (2-3 weeks)

### Phase 4: Autotools Builder

**Goal**: Build Autotools-based packages detected by `maestro repo resolve`.

**Tasks**:
1. Implement Autotools builder:
   ```python
   class AutotoolsBuilder(Builder):
       def configure(self, package, config):
           """Run ./configure script."""
           # Run autoreconf if needed
           if needs_autoreconf(package.dir):
               run(['autoreconf', '-i'], cwd=package.dir)

           configure_args = [
               './configure',
               f'--prefix={config.install_prefix}',
               f'CC={config.cc}',
               f'CXX={config.cxx}',
               f'CFLAGS={config.cflags}',
               f'CXXFLAGS={config.cxxflags}',
           ]

           if config.build_type == 'Debug':
               configure_args.append('--enable-debug')

       def build_package(self, package, config):
           """Build using make."""
           make_args = ['make']
           if config.parallel:
               make_args.extend(['-j', str(config.jobs)])
   ```

2. Support Autotools features:
   - Automatic configure script generation (autoreconf)
   - Custom configure options
   - In-source vs out-of-source builds
   - Cross-compilation support
   - VPATH builds

3. Handle Autotools variants:
   - GNU Make
   - BSD Make
   - Configure.ac options parsing

**Deliverables**:
- Autotools builder that can build Autotools packages
- Support for configure options
- Cross-compilation support

**Estimated Complexity**: Medium (2-3 weeks)

### Phase 5: Visual Studio / MSBuild Builder

**Goal**: Build Visual Studio projects detected by `maestro repo resolve`.

**Tasks**:
1. Implement MSBuild builder:
   ```python
   class MSBuildBuilder(Builder):
       def build_package(self, package, config):
           """Build using MSBuild."""
           msbuild_args = [
               'msbuild',
               package.metadata['project_file'],
               f'/p:Configuration={config.configuration}',
               f'/p:Platform={config.platform}',
               f'/maxcpucount:{config.jobs}',
           ]

           if config.verbose:
               msbuild_args.append('/v:detailed')
   ```

2. Support Visual Studio features:
   - Configuration selection (Debug, Release)
   - Platform selection (Win32, x64, ARM, ARM64)
   - Solution builds (multiple projects)
   - Project dependency resolution
   - Custom build events

3. Support both MSBuild and legacy builds:
   - .vcxproj / .csproj (MSBuild format)
   - .vcproj (legacy VCBuild format)
   - Solution (.sln) builds

**Deliverables**:
- MSBuild builder for Visual Studio projects
- Support for all configurations and platforms
- Solution-level builds with dependency ordering

**Estimated Complexity**: Medium (2-3 weeks)

### Phase 5.5: Maven Builder

**Goal**: Build Maven projects detected by `maestro repo resolve`.

**Tasks**:
1. Implement Maven builder:
   ```python
   class MavenBuilder(Builder):
       def build_package(self, package, config):
           """Build using Maven (mvn)."""
           mvn_args = ['mvn']

           # Build goals
           if config.clean:
               mvn_args.append('clean')
           mvn_args.append('package')  # or install, compile, etc.

           # Configuration
           if config.skip_tests:
               mvn_args.append('-DskipTests')

           # Parallel builds
           if config.jobs > 1:
               mvn_args.append(f'-T{config.jobs}')

           # Profile activation
           if config.profile:
               mvn_args.append(f'-P{config.profile}')

           # Offline mode
           if config.offline:
               mvn_args.append('--offline')

           # Execute from pom.xml directory
           return self.execute(mvn_args, cwd=package.dir)
   ```

2. Support Maven features:
   - Multi-module builds (reactor builds)
   - Profile activation (-P flag)
   - Offline mode (--offline)
   - Parallel module builds (-T flag)
   - Lifecycle phases (clean, compile, test, package, install, deploy)
   - Plugin goals (e.g., mvn native:compile for native modules)
   - Property overrides (-D flags)

3. Handle Maven-specific packaging:
   - JAR packaging (standard Java libraries)
   - WAR packaging (web applications)
   - AAR packaging (Android libraries)
   - POM packaging (parent POMs)
   - Native module builds (JNI, FluidSynth, etc.)

**Deliverables**:
- Maven builder that can build Maven projects
- Support for multi-module reactor builds
- Profile and property configuration
- Native plugin support for JNI modules

**Estimated Complexity**: Low-Medium (1-2 weeks)

### Phase 6: Universal Build Configuration

**Goal**: Unified configuration system for all build systems.

**Tasks**:
1. Design unified build configuration format:
   ```toml
   # .maestro/methods/gcc-debug.toml
   [method]
   name = "gcc-debug"
   builder = "gcc"

   [compiler]
   cc = "gcc"
   cxx = "g++"

   [flags]
   cflags = ["-g", "-O0", "-Wall"]
   cxxflags = ["-g", "-O0", "-Wall", "-std=c++17"]
   ldflags = ["-g"]

   [config]
   build_type = "Debug"
   parallel = true
   jobs = 8

   [platform]
   os = "linux"
   arch = "x86_64"
   ```

2. Implement method auto-detection:
   - Detect available compilers (GCC, Clang, MSVC)
   - Detect CMake, Make, MSBuild
   - Create default methods for each
   - Store in `.maestro/methods/`

3. Support method inheritance:
   ```toml
   # gcc-release.toml inherits from gcc-debug.toml
   [method]
   name = "gcc-release"
   inherit = "gcc-debug"

   [flags]
   cflags = ["-O2", "-DNDEBUG"]
   cxxflags = ["-O2", "-DNDEBUG", "-std=c++17"]
   ldflags = []

   [config]
   build_type = "Release"
   ```

4. Support per-package overrides:
   - Store in `.maestro/packages/<package>/method.toml`
   - Allow package-specific flags
   - Allow package-specific builder selection

**Deliverables**:
- Unified build configuration format
- Method auto-detection
- Method inheritance
- Per-package overrides

**Estimated Complexity**: Medium (2-3 weeks)

### Phase 7: CLI Integration

**Goal**: Expose build functionality through `maestro make` command.

**Tasks**:
1. Implement `maestro make` command structure:
   ```
   maestro make build [PACKAGE] [OPTIONS]
       Build one or more packages

       Options:
           --method METHOD       Build method to use (default: auto)
           --config CONFIG       Build configuration for U++ packages
           --jobs N              Parallel jobs (default: CPU count)
           --target TARGET       Override output target path
           --verbose             Show full build commands
           --clean-first         Clean before building

   maestro make clean [PACKAGE]
       Clean build artifacts for package(s)

   maestro make rebuild [PACKAGE] [OPTIONS]
       Clean and build package(s)

   maestro make config
       Configure build methods and options

       Subcommands:
           list                  List available methods
           show METHOD           Show method configuration
           edit METHOD           Edit method configuration
           detect                Auto-detect and create methods

   maestro make export [PACKAGE] [FORMAT]
       Export package to other build system format

       Formats:
           makefile              GNU Makefile
           cmake                 CMakeLists.txt
           msbuild               Visual Studio project
           ninja                 Ninja build file

   maestro make methods
       List all available build methods

   maestro make android [OPTIONS]
       Build Android APK

       Options:
           --sdk-path PATH       Android SDK path (default: auto-detect)
           --ndk-path PATH       Android NDK path (default: auto-detect)
           --platform VERSION    Android platform (e.g., android-30)
           --arch ARCH           Target architecture(s) (armeabi-v7a, arm64-v8a, x86, x86_64)
           --keystore PATH       Keystore for signing
           --install             Install to device after building
           --run                 Run app after installing

   maestro make jar [PACKAGE] [OPTIONS]
       Build Java JAR

       Options:
           --main-class CLASS    Main class for executable JAR
           --manifest PATH       Custom manifest file
           --sign                Sign JAR with jarsigner
   ```

2. Implement package selection:
   - Build by package name: `maestro make build MyPackage`
   - Build by pattern: `maestro make build "core/*"`
   - Build main package: `maestro make build` (from current dir)
   - Build all: `maestro make build --all`

3. Implement method selection:
   - Auto-detect: Use package's native build system
   - Explicit: `maestro make build --method gcc-debug`
   - U++ config: `maestro make build --config "GUI MT"`

4. Implement output formatting:
   - Progress indicator for parallel builds
   - Error highlighting
   - Warning/error count summary
   - Build time reporting

5. Add repository integration:
   - Load packages from `.maestro/repo/index.json`
   - Resolve dependencies using `repo pkg tree`
   - Build packages in dependency order
   - Support for build configuration per package

**Deliverables**:
- Complete `maestro make` CLI
- Integration with `maestro repo` artifacts
- User-friendly output formatting
- Help documentation

**Estimated Complexity**: Medium (3-4 weeks)

### Phase 8: Advanced Features

**Goal**: Port advanced umk features.

**Tasks**:
1. Blitz build (unity build) support:
   - Concatenate multiple .cpp files
   - Automatic blitz file generation
   - Blitz-safe detection (no static variables)
   - Per-file blitz opt-out

2. Precompiled header (PCH) support:
   - PCH generation for frequently used headers
   - Automatic PCH detection
   - Per-file PCH opt-out

3. Binary resource compilation (.brc):
   - Embed binary files into executables
   - Generate C++ arrays from binary data
   - Support compression (gzip, bz2, lzma, zstd)

4. Android builds:
   - **SDK detection and validation**:
     - Auto-detect Android SDK location
     - Validate platform and build-tools versions
     - Tool availability checking (aapt, d8/dx, apksigner, zipalign)
   - **NDK integration**:
     - Auto-detect Android NDK location
     - Multi-architecture builds (armeabi-v7a, arm64-v8a, x86, x86_64)
     - Toolchain selection (clang, gcc)
     - C++ runtime selection (c++_static, c++_shared, system)
   - **Build process implementation**:
     - Java source compilation (javac)
     - Resource compilation (aapt)
     - R.java generation
     - Native library compilation (ndk-build or direct)
     - DEX generation (d8 preferred, dx fallback)
     - APK assembly and packaging
     - APK alignment (zipalign)
     - APK signing (apksigner or jarsigner)
   - **AndroidManifest.xml handling**:
     - Parse existing manifest
     - Validate required fields
     - Support manifest merging
   - **Resource handling**:
     - Package resources with aapt
     - Support resource package flag
     - Handle drawable, layout, values, etc.
   - **Device deployment** (optional):
     - ADB integration
     - Install to device/emulator
     - Launch activity
     - Logcat integration
   - **Build configuration**:
     ```python
     class AndroidBuilder(Builder):
         def configure(self, package, config):
             # SDK setup
             sdk = AndroidSDK.auto_detect()
             ndk = AndroidNDK.auto_detect()

             # Architecture selection
             arches = config.get('architectures', ['armeabi-v7a', 'arm64-v8a'])

             # Build type
             debug = config.build_type == 'Debug'
     ```

5. Java builds:
   - **JDK detection and validation**:
     - Auto-detect JDK location (JAVA_HOME, PATH)
     - Version checking (Java 8, 11, 17, 21)
     - Tool availability (javac, jar, jarsigner)
   - **Compilation pipeline**:
     - Source preprocessing (line ending fixes)
     - Compile .java to .class (javac)
     - Classpath management
     - Debug/Release flags
   - **JAR packaging**:
     - Manifest.mf generation
     - Main-Class specification
     - Classpath in manifest
     - Resource inclusion
     - JAR signing (optional)
   - **JNI support**:
     - Generate JNI headers (javah/javac -h)
     - Link with native libraries
     - Package native libraries in JAR
   - **Build configuration**:
     ```python
     class JavaBuilder(Builder):
         def configure(self, package, config):
             # JDK setup
             jdk = JDK.auto_detect()

             # Compilation options
             javac_opts = ['-encoding', 'UTF-8']
             if config.build_type == 'Debug':
                 javac_opts.append('-g')
             else:
                 javac_opts.append('-g:none')
     ```

6. Export features:
   - Generate Makefile from any package
   - Generate CMakeLists.txt from U++ package
   - Generate Visual Studio project from U++ package
   - Generate Ninja build file

7. Cross-compilation:
   - Toolchain file support
   - Sysroot configuration
   - Host vs target tool selection

**Deliverables**:
- Advanced build features
- Export to multiple formats
- Cross-compilation support
- Android/Java support

**Estimated Complexity**: High (6-8 weeks)

### Phase 9: TUI Integration

**Goal**: Integrate build system into Maestro TUI.

**Tasks**:
1. Add build pane to TUI:
   - Show build progress
   - Display compiler output
   - Highlight errors and warnings
   - Navigate to error locations

2. Build configuration UI:
   - Method selection widget
   - Package selection tree
   - Build options editor
   - Parallel job control

3. Interactive build features:
   - Stop/resume builds
   - Build selected packages
   - Jump to error in editor
   - Filter warnings/errors

**Deliverables**:
- TUI build interface
- Real-time build monitoring
- Error navigation

**Estimated Complexity**: Medium (3-4 weeks)

### Phase 10: Universal Hub System (MaestroHub)

**Goal**: Implement universal package hub for automatic dependency resolution across all build systems.

**Tasks**:
1. **Hub metadata format**:
   - Define JSON schema for hub registries
   - Support UppHub compatibility mode
   - Multi-build-system package metadata
   - Versioning and compatibility tracking

2. **Hub client implementation**:
   ```python
   class MaestroHub:
       def load_hub(self, url):
           """Load hub metadata from URL or local file."""
           pass

       def search_package(self, package_name):
           """Search for package across all registered hubs."""
           pass

       def install_nest(self, nest_name, update=False):
           """Clone/update repository nest."""
           pass

       def auto_resolve(self, workspace):
           """Automatically resolve missing dependencies."""
           pass
   ```

3. **CLI integration**:
   ```
   maestro hub list
       List all registered hubs and nests

   maestro hub search [PACKAGE]
       Search for package in registered hubs

   maestro hub install [NEST]
       Install repository nest from hub

   maestro hub update [NEST]
       Update repository nest to latest version

   maestro hub add [URL]
       Add custom hub registry

   maestro hub sync
       Sync all hub metadata

   maestro hub info [NEST]
       Show detailed information about nest
   ```

4. **Auto-resolution**:
   - Detect missing packages during build
   - Search registered hubs
   - Prompt user for installation
   - Clone repositories to ~/.maestro/hub/
   - Recursive dependency resolution
   - Cache hub metadata for performance

5. **Hub registry management**:
   - Official MaestroHub registry (to be created)
   - Import existing UppHub
   - Custom/private hub support
   - Organization-specific hubs

6. **Package path resolution**:
   - Search order: local project → ~/.maestro/hub/ → system paths
   - Package name disambiguation
   - Version conflict resolution

7. **Integration with existing package managers**:
   - Conan wrapper for C++ packages
   - vcpkg integration
   - npm/pip/cargo bridge (future)

**Deliverables**:
- Universal hub client
- CLI commands for hub management
- Auto-dependency resolution
- UppHub compatibility
- Package search and discovery

**Estimated Complexity**: Medium-High (4-5 weeks)

## Technical Considerations

### 1. Language Choice: Python vs C++

**Decision**: Implement in Python, with option to call C++ umk as subprocess for U++ builds.

**Rationale**:
- Maestro is Python-based - seamless integration
- Easier to maintain and extend
- Python subprocess management is robust
- Can shell out to native umk for U++ packages if needed
- CMake, Autotools, MSBuild are command-line tools anyway

**Hybrid approach** (later optimization):
- Phase 2 can optionally use native umk via subprocess
- Performance-critical parts can be Cython or C++ extensions
- Pure Python initially for maximum portability

### 2. Build Artifact Storage

Store build artifacts in `.maestro/build/` directory:
```
.maestro/build/
├── <method>/
│   ├── <package>/
│   │   ├── obj/          # Object files
│   │   ├── pch/          # Precompiled headers
│   │   ├── deps/         # Dependency files
│   │   ├── classes/      # Java .class files
│   │   ├── dex/          # Android DEX files
│   │   ├── libs/         # Native libraries (.so, .a)
│   │   ├── res/          # Android resources
│   │   └── <target>      # Final executable/library/JAR/APK
│   └── ...
├── cache/                # Build cache (PPInfo, timestamps)
└── android-project/      # Android project structure (for NDK)
    ├── jni/              # JNI sources
    ├── src/              # Java sources
    ├── res/              # Resources
    └── AndroidManifest.xml
```

### 3. Dependency Tracking

Two-level dependency system:
1. **Package-level**: Use `maestro repo pkg tree` to resolve package dependencies
2. **File-level**: Track header/source dependencies for incremental builds

Store file-level dependencies in `.maestro/build/cache/deps/<package>.json`:
```json
{
  "src/main.cpp": {
    "mtime": 1234567890,
    "includes": ["utils.h", "Core/Core.h"],
    "defines": ["GUI", "MT"],
    "object": ".maestro/build/gcc-debug/MyPackage/obj/main.o"
  }
}
```

### 4. Parallel Build Management

Use Python `multiprocessing` or `concurrent.futures`:
- One process per compilation unit
- Respect `--jobs` limit
- Collect stdout/stderr from each process
- Aggregate errors and warnings
- Display progress indicator

### 5. Cross-Build System Compatibility

Support building packages detected from different build systems:

**U++ package** with CMake dependencies:
```
MyUppPackage (u++)
├── uses CoreLib (u++)
└── uses ThirdPartyLib (cmake)
```

Strategy:
1. Build ThirdPartyLib using CMake builder
2. Collect include paths and libraries from CMake install
3. Pass to U++ builder as additional includes/libraries

**CMake package** with Autotools dependencies:
```
MyCmakePackage (cmake)
└── depends_on zlib (autotools)
```

Strategy:
1. Build zlib using Autotools builder
2. Install to staging area
3. Pass install prefix to CMake via -D flags

### 6. Build Method Detection

Auto-detect build method based on package metadata:
```python
def select_builder(package):
    if package.build_system == 'upp':
        return UppBuilder()
    elif package.build_system == 'cmake':
        return CMakeBuilder()
    elif package.build_system == 'autoconf':
        return AutotoolsBuilder()
    elif package.build_system == 'msvs':
        return MSBuildBuilder()
    else:
        raise ValueError(f"Unknown build system: {package.build_system}")
```

## File Structure

Proposed file structure in Maestro repository:

```
maestro/
├── builders/
│   ├── __init__.py
│   ├── base.py              # Abstract Builder base
│   ├── upp.py               # U++ builder (port of umk)
│   ├── gcc.py               # GCC/Clang builder (for U++)
│   ├── msvc.py              # MSVC builder (for U++)
│   ├── cmake.py             # CMake builder
│   ├── autotools.py         # Autotools builder
│   ├── msbuild.py           # MSBuild builder
│   ├── make.py              # Generic Make builder
│   ├── host.py              # Host abstraction (local/remote)
│   ├── console.py           # Process management
│   ├── config.py            # Build method configuration
│   ├── workspace.py         # Workspace and dependency resolution
│   ├── package.py           # Package abstraction
│   ├── ppinfo.py            # Preprocessor dependency tracking
│   ├── blitz.py             # Blitz build support
│   ├── cache.py             # Build cache management
│   ├── export.py            # Project export
│   ├── android_sdk.py       # Android SDK detection and management
│   ├── android_ndk.py       # Android NDK integration
│   ├── android_manifest.py  # AndroidManifest.xml parsing
│   ├── apk.py               # APK packaging and signing
│   ├── jdk.py               # JDK detection and management
│   └── jar.py               # JAR packaging
├── make/
│   ├── __init__.py
│   └── cli.py               # maestro make CLI implementation
├── hub/
│   ├── __init__.py
│   ├── client.py            # Hub client and metadata fetching
│   ├── resolver.py          # Dependency auto-resolution
│   └── cli.py               # maestro hub CLI implementation
├── repo/
│   └── build_systems.py     # [existing] Build system detection
└── main.py                  # [existing] Main CLI entry
```

## Integration Points

### 1. With `maestro repo resolve`

The `maestro repo resolve` command already detects packages and their build systems. The `maestro make` command will:
- Load package index from `.maestro/repo/index.json`
- Use package metadata (build_system, dir, files) to configure builders
- Resolve dependencies using existing `repo pkg tree` logic

### 2. With Build Methods

U++ build methods stored in `~/.upp/` can be:
- Imported to `.maestro/methods/`
- Converted to unified TOML format
- Augmented with CMake/Autotools/MSBuild settings

### 3. With TUI

The TUI can:
- Display build progress in real-time
- Show compiler errors with file navigation
- Allow interactive package selection
- Provide build configuration UI

### 4. With Universal Hub (MaestroHub)

The hub system integrates with build and repository scanning:
- **During build**: Auto-detect missing packages and offer installation from hub
- **Repository search**: `maestro repo resolve` can search hub for missing dependencies
- **Package queries**: `maestro repo pkg search` can extend to hub packages
- **Build methods**: Hub can distribute build method configurations
- **Workspace sync**: Automatically keep hub packages up-to-date

**Package resolution order**:
1. Local project directory
2. `~/.maestro/hub/` (hub-installed packages)
3. System paths (if configured)

**Hub + Build workflow**:
```bash
# User builds project
$ maestro make build MyApp

# Build system scans dependencies
[maestro] Scanning package MyApp...
[maestro] Found dependency: CoreLib (local)
[maestro] Found dependency: DrawLib (local)
[maestro] Missing dependency: PluginSDK

# Hub auto-resolution kicks in
[maestro] Searching MaestroHub for PluginSDK...
[maestro] Found in nest 'third-party-libs'
[maestro] Install third-party-libs? [Y/n] y
[maestro] Cloning https://github.com/org/third-party-libs...
[maestro] Installing PluginSDK...

# Build continues
[maestro] Building CoreLib...
[maestro] Building DrawLib...
[maestro] Building PluginSDK...
[maestro] Linking MyApp...
[maestro] Build successful!
```

## Testing Strategy

### Unit Tests
- Test each builder independently
- Mock package structures
- Test configuration parsing
- Test dependency resolution

### Integration Tests
- Test complete build workflows
- Use test repositories:
  - ai-upp (U++ project)
  - TopGuitar/TuxGuitar (Maven multi-module project)
  - StuntCarStadium (Unity/CMake/Visual Studio)
  - Tesseract-Sauerbraten (Autotools)
  - CodexSandbox projects (various)

### Performance Tests
- Measure build times vs native tools
- Test parallel build scaling
- Test incremental build correctness

## Success Metrics

1. **Correctness**: Builds produce byte-identical outputs to native tools
2. **Performance**: Within 10% of native tool performance
3. **Usability**: Single command to build any detected package
4. **Coverage**: Support 90%+ of common build system features

## Risks and Mitigations

### Risk 1: Complexity of U++ Build System
**Mitigation**:
- Start with simple U++ packages
- Gradually add features (blitz, PCH, etc)
- Option to shell out to native umk if needed

### Risk 2: Cross-Build-System Dependencies
**Mitigation**:
- Design builder interface to support artifact handoff
- Use staging directories for cross-builder integration
- Document limitations and workarounds

### Risk 3: Platform-Specific Build Issues
**Mitigation**:
- Test on Linux, Windows, macOS
- Use platform-specific builder variants
- Leverage umk's existing platform support

### Risk 4: Performance of Python Implementation
**Mitigation**:
- Profile early and optimize hot paths
- Use multiprocessing for parallelism
- Consider Cython for critical code
- Option to use native umk as backend

### Phase 11: Internal Package Groups

**Goal**: Implement internal package grouping for better organization and navigation.

**Background**:
U++ packages use **separators** to organize files into logical groups within a package. A separator is a file entry with the `separator` flag that acts as a group title. Files following a separator belong to that group until the next separator.

**Example from CtrlCore.upp**:
```
file
    Core readonly separator,        # Group title: "Core"
    CtrlCore.h,                      # → belongs to "Core" group
    MKeys.h,                         # → belongs to "Core" group
    ...
    Win32 readonly separator,        # Group title: "Win32"
    Win32Gui.h,                      # → belongs to "Win32" group
    ...
    X11 readonly separator,          # Group title: "X11"
    X11Gui.h,                        # → belongs to "X11" group
    ...
```

**Use Cases**:
1. **U++ packages**: Display and navigate file groups in TUI
2. **Misc packages**: Auto-group files by extension/type
3. **Multi-language packages**: Organize by language (Python, C++, Java)
4. **Documentation packages**: Group by topic
5. **Build support**: Build specific groups only

**Tasks**:

1. **Group representation in package metadata**:
   ```python
   @dataclass
   class FileGroup:
       """Internal package file group."""
       name: str                    # Group name/title
       files: List[str]             # Files in this group
       readonly: bool = False       # From separator flags
       auto_generated: bool = False # True if auto-grouped

   @dataclass
   class PackageInfo:
       # ... existing fields ...
       groups: List[FileGroup] = field(default_factory=list)
       ungrouped_files: List[str] = field(default_factory=list)
   ```

2. **U++ separator parsing enhancement**:
   - Already detected in `upp_parser.py:262-263`
   - Extract separator name (first token in file entry)
   - Build group structure from separator markers
   - Preserve readonly and other flags
   - Handle multiple separators
   - Support quoted separator names with spaces

3. **Auto-grouping for misc packages**:
   ```python
   class AutoGrouper:
       """Automatically group files by patterns."""

       GROUP_RULES = {
           'Documentation': ['.md', '.txt', '.rst', '.adoc'],
           'Scripts': ['.sh', '.bash', '.zsh', '.py', '.js'],
           'Configuration': ['.toml', '.yaml', '.yml', '.json', '.ini', '.conf'],
           'Build Files': ['Makefile', '.gradle', '.gradle.kts', 'pom.xml',
                          'CMakeLists.txt', 'configure.ac'],
           'Python': ['.py'],
           'C/C++': ['.c', '.cpp', '.cc', '.cxx', '.h', '.hpp'],
           'Java': ['.java'],
           'Kotlin': ['.kt', '.kts'],
           'Web': ['.html', '.css', '.js', '.ts', '.jsx', '.tsx'],
           'Data': ['.json', '.xml', '.csv', '.tsv', '.sql'],
           'Images': ['.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico'],
           'Other': [],  # Catch-all
       }

       def auto_group(self, files: List[str]) -> List[FileGroup]:
           """Group files by extension/pattern."""
           groups = defaultdict(list)

           for file in files:
               matched = False
               for group_name, patterns in self.GROUP_RULES.items():
                   if group_name == 'Other':
                       continue
                   if any(file.endswith(ext) for ext in patterns):
                       groups[group_name].append(file)
                       matched = True
                       break
                   if any(pattern in file for pattern in patterns):
                       groups[group_name].append(file)
                       matched = True
                       break

               if not matched:
                   groups['Other'].append(file)

           return [
               FileGroup(name=name, files=sorted(files), auto_generated=True)
               for name, files in sorted(groups.items())
               if files  # Only include non-empty groups
           ]
   ```

4. **CLI support**:
   ```
   maestro repo pkg [ID] --show-groups
       Show package with file groups

   maestro repo pkg [ID] --group [GROUP]
       Filter to specific group

   Example output:
   ============================================================
                   PACKAGE: CtrlCore (U++)
   ============================================================

   Root path: /home/sblo/upp/uppsrc/CtrlCore
   Groups: 6
   Total files: 135

   ────────────────────────────────────────────────────────────
     GROUP: Core (21 files)
     CtrlCore.h
     MKeys.h
     stdids.h
     SystemDraw.cpp
     Frame.cpp
     ... (16 more)

   ────────────────────────────────────────────────────────────
     GROUP: Win32 (22 files)
     Win32Gui.h
     Win32GuiA.h
     Win32Keys.h
     DrawWin32.cpp
     ... (18 more)

   ────────────────────────────────────────────────────────────
     GROUP: X11 (22 files)
     X11Gui.h
     X11GuiA.h
     X11Keys.h
     ... (19 more)
   ```

5. **TUI support**:
   - Show groups in package view (collapsible tree)
   - Navigate between groups (Tab/Shift+Tab)
   - Filter/search within group
   - Show group statistics (file count, LOC)
   - Syntax highlighting for group headers

6. **Build integration**:
   - `maestro make build [PACKAGE] --group [GROUP]` - Build specific group only
   - Useful for platform-specific builds (build only Win32 group, only X11 group)
   - Dependency tracking per group

7. **Export support**:
   - Export groups to IDE project structures
   - Visual Studio filters (.vcxproj.filters)
   - CMake source_group()
   - IntelliJ modules

**Example: Misc Package Auto-Grouping**:
```
maestro repo pkg 19 --show-groups

============================================================
            INTERNAL PACKAGE: root_misc
============================================================

Root path: /common/active/sblo/Dev/RainbowGame/trash
Type: misc
Groups: 7 (auto-generated)
Total files: 67

────────────────────────────────────────────────────────────
  GROUP: Documentation (25 files)
  AGENTS.md
  COMPLETION_NOTICE.md
  CONVERSION_COMMITS.md
  CPP_NOTES.txt
  CPP_TASKS.md
  ... (20 more)

────────────────────────────────────────────────────────────
  GROUP: Scripts (4 files)
  build-cpp.sh
  build.sh
  create_all_stubs.sh
  create_all_stubs_final.sh

────────────────────────────────────────────────────────────
  GROUP: Python (3 files)
  extract_ast.py
  format_commits_md.py
  full_pseudocode_generator.py

────────────────────────────────────────────────────────────
  GROUP: Build Files (2 files)
  build.gradle.kts
  env.sh

────────────────────────────────────────────────────────────
  GROUP: Data (2 files)
  codex-history.txt
  file_list.txt

────────────────────────────────────────────────────────────
  GROUP: Other (31 files)
  .gradle
  Book
  LICENSE
  README.md
  android
  ... (26 more)
```

**Deliverables**:
- Group representation in package metadata
- U++ separator parsing with group extraction
- Auto-grouping for misc packages
- CLI support for viewing and filtering groups
- TUI integration with collapsible group view
- Build support for group-specific compilation
- Export to IDE project structures

**Estimated Complexity**: Medium (2-3 weeks)

## Timeline Estimate

| Phase | Duration | Dependencies |
|-------|----------|--------------|
| Phase 1: Core Builder Abstraction | 2-3 weeks | None |
| Phase 2: U++ Builder Implementation | 4-6 weeks | Phase 1 |
| Phase 3: CMake Builder | 2-3 weeks | Phase 1 |
| Phase 4: Autotools Builder | 2-3 weeks | Phase 1 |
| Phase 5: MSBuild Builder | 2-3 weeks | Phase 1 |
| Phase 5.5: Maven Builder | 1-2 weeks | Phase 1 |
| Phase 6: Universal Build Configuration | 2-3 weeks | Phases 2-5.5 |
| Phase 7: CLI Integration | 3-4 weeks | Phases 2-6 |
| Phase 8: Advanced Features | 6-8 weeks | Phase 7 |
| Phase 9: TUI Integration | 3-4 weeks | Phase 7 |
| Phase 10: Universal Hub System | 4-5 weeks | Phases 2-7 |
| Phase 11: Internal Package Groups | 2-3 weeks | Phase 7 |

**Total Estimate**: 33-49 weeks (8-11 months)

**Minimum Viable Product (MVP)**: Phases 1-2 (6-9 weeks)
- Core builder framework
- U++ package building
- Basic CLI

**Extended MVP**: Phases 1-7 (17-25 weeks)
- All builder types
- Universal configuration
- Complete CLI

**Full Feature Set**: Phases 1-11 (33-49 weeks)
- Advanced features (Android, Java, Blitz, PCH)
- TUI integration
- Universal Hub system
- Internal package groups

## Future Extensions

1. **Distributed Builds**: Remote builder execution (distcc-style)
2. **Build Caching**: CCache/sccache integration
3. **Containerized Builds**: Docker/Podman integration for reproducible builds
4. **Cloud Builds**: AWS/GCP/Azure builder backends
5. **IDE Integration**: Language Server Protocol (LSP) for compile_commands.json
6. **Package Management**: Binary artifact caching and distribution
7. **Continuous Integration**: GitHub Actions / GitLab CI integration
8. **Build Analytics**: Build time tracking, bottleneck detection
9. **MaestroHub Enhancements**:
   - Binary package distribution (pre-built artifacts)
   - Package versioning and semver support
   - Dependency version resolution and conflict detection
   - Private/authenticated hubs for proprietary packages
   - Hub mirroring and CDN support
   - Package security scanning and vulnerability tracking
10. **Cross-Ecosystem Bridges**:
    - npm package integration for JavaScript/TypeScript projects
    - pip package integration for Python projects
    - cargo package integration for Rust projects
    - NuGet package integration for .NET projects
    - Maven/Gradle integration for Java projects

## References

### U++ Documentation
- U++ Builder system: https://www.ultimatepp.org/srcdoc$ide$Builders$en-us.html
- U++ Build methods: https://www.ultimatepp.org/srcdoc$ide$CoreTutorial$en-us.html

### CMake
- CMake documentation: https://cmake.org/documentation/

### Autotools
- GNU Autotools: https://www.gnu.org/software/automake/manual/

### MSBuild
- MSBuild reference: https://learn.microsoft.com/en-us/visualstudio/msbuild/

## Conclusion

The integration of umk into Maestro will create a powerful universal build system that leverages existing build system detection to provide a unified build experience across U++, CMake, Autotools, and Visual Studio projects. The phased approach allows for incremental development and testing, with clear milestones and deliverables.

The Python implementation ensures tight integration with Maestro's existing infrastructure while maintaining the flexibility to optimize performance-critical paths or fall back to native tools when needed.
