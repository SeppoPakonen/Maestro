# Phase AS1 — Assemblies in Maestro Repository System

**Objective**: Organize packages into logical assemblies that represent cohesive units of code, rather than treating every directory as a potential package.

## Tasks

- [ ] **AS1.1: Assembly Concept Implementation**
  - [ ] Create `maestro repo asm` command group
  - [ ] Implement `maestro repo asm list` - List all assemblies in repository
  - [ ] Implement `maestro repo asm help` - Show help for assembly commands  
  - [ ] Implement `maestro repo asm <asm>` - Operations on specific assembly
  - [ ] Add additional assembly-specific operations

- [ ] **AS1.2: Assembly Type Classification**
  - [ ] Implement U++ type assemblies: Have U++ package directories and are NOT package directories
  - [ ] Implement Programming language assemblies: For specific languages (Python, Java, etc.)
  - [ ] Implement Misc-type assembly: For other packages that don't fit specific language patterns
  - [ ] Plan Documentation-type assembly: (Future support) For documentation projects

- [ ] **AS1.3: Assembly Detection & Classification**
  - [ ] Implement U++ assembly detection: Detected by presence of multiple `.upp` files or structured package organization  
  - [ ] Implement Python assembly detection: Detected by presence of setup.py files in subdirectories
  - [ ] Implement Java assembly detection: Detected by maven/gradle project structure
  - [ ] Implement other language assembly detection: Based on specific build files and directory structure

- [ ] **AS1.4: Assembly Examples Implementation**
  - [ ] Support Python assembly structure (directories with sub-directories containing setup.py)
  - [ ] Support Java assembly structure (e.g., `~/Dev/TopGuitar/desktop/`, `~/Dev/TopGuitar/common/`)
  - [ ] Handle multi-type assembly handling correctly

- [ ] **AS1.5: Multi-type Assembly Handling**  
  - [ ] Ensure Gradle assembly correctly handles packages like `~/Dev/RainbowGame/trash/` (packages: desktop, core, ...)
  - [ ] Ensure U++ assembly correctly handles `~/Dev/RainbowGame/trash/uppsrc`
  - [ ] Implement proper system to apply appropriate build systems to appropriate assemblies
  - [ ] Handle dependencies between different assembly types correctly
  - [ ] Provide focused tooling for each assembly type