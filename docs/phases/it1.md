# Phase IT1 — Integration Testing

## Integration Test Plan

### Test Repositories Matrix

| Repository | Build Systems | Focus Area |
|------------|---------------|------------|
| `~/Dev/ai-upp` | U++ | U++ builder, workspace resolution |
| `~/Dev/TopGuitar` | Maven, U++ | Maven multi-module, mixed builds |
| `~/Dev/StuntCarStadium` | Unity, Visual Studio, CMake | MSBuild, multi-system |
| `~/Dev/Maestro` | Python (setuptools) | Python builder |
| `~/Dev/AgentManager` | npm (monorepo) | Node.js builder, workspaces |
| `~/Dev/BruceKeith/src/NeverScript` | Go modules | Go builder |
| `~/Dev/pedigree` | CMake | CMake builder, complex OS project |
| `~/Dev/pedigree-apps` | pup (Python packages) | pup builder, Portage-like system |

## Test Workflows

1. **Basic Build Test**:
   ```bash
   cd <repository>
   maestro repo resolve
   maestro make build
   ```

2. **Clean Build Test**:
   ```bash
   maestro make clean
   maestro make build
   ```

3. **Incremental Build Test**:
   ```bash
   # Modify source file
   maestro make build
   # Should rebuild only affected files
   ```

4. **Parallel Build Test**:
   ```bash
   maestro make build --jobs 8
   ```

5. **Mixed Build System Test**:
   ```bash
   cd ~/Dev/TopGuitar
   maestro make build  # Should build both Maven and U++ packages
   ```

6. **Hub Integration Test**:
   ```bash
   # Project with missing dependency
   maestro make build
   # Should prompt to install from hub
   ```

7. **External Dependency Test**:
   ```bash
   # Project with git submodules
   maestro make build
   # Should initialize and build submodules
   ```

## Tasks

- [ ] **IT1.1: CI/CD Pipeline Setup**
  - [ ] Set up CI/CD pipeline
  - [ ] Configure automated testing
  - [ ] Set up build triggers

- [ ] **IT1.2: Multi-Platform Testing**
  - [ ] Test on Linux platforms
  - [ ] Test on Windows platforms  
  - [ ] Test on macOS platforms
  - [ ] Test with different compiler versions

- [ ] **IT1.3: Regression Testing**
  - [ ] Implement regression testing for each phase
  - [ ] Automate test execution
  - [ ] Set up test reporting