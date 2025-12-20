# Phase umk11: Internal Package Groups 📋 **[Planned]**

**Reference**: `docs/umk.md` Phase 11
**Duration**: 2-3 weeks
**Dependencies**: Phase 7

## Background

U++ packages use **separators** to organize files into logical groups within a package. A separator is a file entry with the `separator` flag that acts as a group title. Files following a separator belong to that group until the next separator.

Example from `CtrlCore.upp`:
```
file
    Core readonly separator,        # Group: "Core"
    CtrlCore.h,                      # → belongs to "Core" group
    MKeys.h,
    Win32 readonly separator,        # Group: "Win32"
    Win32Gui.h,                      # → belongs to "Win32" group
    X11 readonly separator,          # Group: "X11"
    X11Gui.h,                        # → belongs to "X11" group
```

For misc packages (root files), auto-group by file type:
- Documentation: .md, .txt, .rst files
- Scripts: .sh, .py, .js files
- Build Files: Makefile, CMakeLists.txt, build.gradle, etc.
- Python/Java/C++: Language-specific groups
- Other: Catch-all for remaining files

## Tasks

- [ ] **11.1: Group Representation**
  - [ ] Create `FileGroup` dataclass in package metadata
  - [ ] Add `groups` and `ungrouped_files` fields to `PackageInfo`
  - [ ] Support readonly flag on groups

- [ ] **11.2: U++ Separator Parsing**
  - [ ] Enhance `upp_parser.py` to extract separator names
  - [ ] Build group structure from separator markers
  - [ ] Handle multiple consecutive separators
  - [ ] Support quoted separator names with spaces

- [ ] **11.3: Auto-Grouping for Misc Packages**
  - [ ] Create `AutoGrouper` class
  - [ ] Define GROUP_RULES for file extensions
  - [ ] Implement pattern matching for file grouping
  - [ ] Group by extension and file patterns
  - [ ] Sort groups and files within groups

- [ ] **11.4: CLI Support**
  - [ ] Implement `maestro repo pkg [ID] --show-groups`
  - [ ] Implement `maestro repo pkg [ID] --group [GROUP]`
  - [ ] Display group headers with file counts
  - [ ] Support collapsed/expanded view

- [ ] **11.5: TUI Integration**
  - [ ] Show groups in package view (collapsible tree)
  - [ ] Navigate between groups (Tab/Shift+Tab)
  - [ ] Filter/search within group
  - [ ] Show group statistics (file count, LOC)
  - [ ] Syntax highlighting for group headers

- [ ] **11.6: Build Integration**
  - [ ] Implement `maestro make build [PACKAGE] --group [GROUP]`
  - [ ] Build specific group only (useful for platform-specific code)
  - [ ] Dependency tracking per group

- [ ] **11.7: Export Support**
  - [ ] Export groups to Visual Studio filters (.vcxproj.filters)
  - [ ] Export groups to CMake source_group()
  - [ ] Export groups to IntelliJ modules

## Deliverables:
- Group representation in package metadata
- U++ separator parsing with group extraction
- Auto-grouping for misc packages
- CLI support for viewing and filtering groups
- TUI integration with collapsible group view
- Build support for group-specific compilation
- Export to IDE project structures

## Test Criteria:
- U++ packages with separators parse correctly
- Groups display in CLI output
- Misc packages auto-group by extension
- Platform-specific group builds work (e.g., build only Win32 group)
- Export to IDE formats preserves group structure
