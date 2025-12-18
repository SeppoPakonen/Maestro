# Phase IT2 — Notes and Considerations

## Tasks

- [ ] **IT2.1: Build Artifact Storage Implementation**
  - [ ] Implement storage of build artifacts in `.maestro/build/` directory
  - [ ] Create method-specific subdirectories (`.maestro/build/<method>/`)
  - [ ] Create package-specific directories (`.maestro/build/<method>/<package>/`)
  - [ ] Implement object file storage (`.maestro/build/<method>/<package>/obj/`)
  - [ ] Implement precompiled headers storage (`.maestro/build/<method>/<package>/pch/`)
  - [ ] Implement dependency tracking file storage (`.maestro/build/<method>/<package>/deps/`)
  - [ ] Implement cache directory structure (`.maestro/build/cache/`)

- [ ] **IT2.2: Dependency Tracking Implementation**
  - [ ] Implement two-level dependency system (package-level and file-level)
  - [ ] Support package-level dependencies using `maestro repo pkg tree`
  - [ ] Implement file-level dependency tracking for header/source dependencies
  - [ ] Store file-level dependencies in `.maestro/build/cache/deps/<package>.json`

- [ ] **IT2.3: Portage Integration Strategy Implementation**
  - [ ] Ensure Phase A2 (Design) gets architecture right before implementation
  - [ ] Start with minimal viable interface and expand as needed
  - [ ] Test with real ebuilds early to validate design decisions
  - [ ] Document limitations honestly
  - [ ] Focus on flexibility to ensure superset can handle future requirements

- [ ] **IT2.4: USE Flag System Implementation**
  - [ ] Support Portage-style USE flags (feature flags)
  - [ ] Support umk-style flags (GUI, MT, DEBUG)
  - [ ] Support multi-configuration builds (umk)
  - [ ] Support single-configuration builds (Portage)
  - [ ] Allow host package USE flag recognition

- [ ] **IT2.5: Development Priorities and Scheduling**
  - [ ] Prioritize Phases 1-7 (Core functionality - Universal Build System) as highest priority
  - [ ] Prioritize Phases TU1-TU6 (TU/AST system) as high priority
  - [ ] Implement TU1-TU3 (Core parsing and symbol resolution) for AI workflows MVP
  - [ ] Implement TU4-TU6 (Auto-completion and transformation) for enhanced IDE features
  - [ ] Prioritize Phase 10 (Hub system) as high priority
  - [ ] Prioritize Phases E1-E4 (Extended build systems) as medium priority
  - [ ] Prioritize Phase 8 (Advanced features) as medium priority
  - [ ] Prioritize Phase 9 (TUI integration) as medium priority
  - [ ] Handle Phases A1-A6 (Portage integration) as Research & Design Phase (requires E4 knowledge)

- [ ] **IT2.6: Learning Progression Setup**
  - [ ] Implement pup support (Phase E4) first: simpler Python-based package system, no USE flags
  - [ ] Progress to Portage (Phases A2-A6): Complex bash-based system with USE flags
  - [ ] Ensure pup provides similar concepts (build phases, dependencies, patches) without Portage's complexity

- [ ] **IT2.7: Parallel Development Tracking**
  - [ ] Support parallel development of UMK Integration and TU/AST
  - [ ] Ensure both use repository scanning (`maestro repo resolve`)
  - [ ] Ensure both need build configuration (`maestro repo conf`)
  - [ ] Ensure TU/AST provides context to AI for `maestro build` workflows

- [ ] **IT2.8: Timeline and Milestone Planning**
  - [ ] Plan Core Universal Build System (Phases 1-7): 17-25 weeks (~4-6 months)
  - [ ] Plan TU/AST System (Phases TU1-TU6): 17-23 weeks (~4-6 months)
  - [ ] Plan TU/AST MVP (TU1-TU3): 9-12 weeks (~2-3 months)
  - [ ] Plan Extended TU/AST (TU4-TU6): 8-11 weeks (~2-3 months)
  - [ ] Plan Extended Build Systems (E1-E4): 8-12 weeks (~2-3 months)
  - [ ] Plan Python (E1): 2-3 weeks
  - [ ] Plan Node.js (E2): 2-3 weeks
  - [ ] Plan Go (E3): 2-3 weeks
  - [ ] Plan pup (E4): 2-3 weeks
  - [ ] Plan Advanced Features (Phase 8): 6-8 weeks (~1.5-2 months)
  - [ ] Plan Hub System (Phase 10): 4-5 weeks (~1 month)
  - [ ] Plan Internal Package Groups (Phase 11): 2-3 weeks (~0.5 month)
  - [ ] Plan Portage Integration (A1-A6): 22-31 weeks (~5-7 months, includes research)
  - [ ] Plan Total Estimate: 76-107 weeks (~18-25 months for everything)
  - [ ] Plan MVP Timeline (Phases 1-7): 17-25 weeks (~4-6 months)
  - [ ] Plan TU/AST MVP (Phases TU1-TU3): 9-12 weeks (~2-3 months)

- [ ] **IT2.9: Development Path Implementation**
  - [ ] Begin with Core Build System (Phases 1-7): 17-25 weeks
  - [ ] Follow with TU/AST MVP (Phases TU1-TU3): 9-12 weeks ← Enables AI workflows
  - [ ] Follow with pup Support (Phase E4): 2-3 weeks ← Learn from simpler Portage-like system
  - [ ] Follow with TU/AST Full (Phases TU4-TU6): 8-11 weeks ← IDE features
  - [ ] Follow with Portage Integration (A1-A6): 22-31 weeks