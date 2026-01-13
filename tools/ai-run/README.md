# ai-run (2026 Edition)

`ai-run` is a next-generation AI orchestration CLI and script interpreter. It serves as the intelligent execution layer for the **Maestro** project management system.

## Features

- **Interpreter Mode:** Support for `#!/usr/bin/env ai-run`.
- **Maestro Context Awareness:** Automatically injects Track, Phase, Task, and Runbook metadata into prompts.
- **Self-Healing Loop (`--fix`):** Automatically captures errors from failing scripts and re-prompts the AI for a fix.
- **Debate Mode (`--debate`):** Orchestrates a multi-model consensus by consulting multiple backends and a judge.
- **Interactive Pause (`--step`):** Pauses execution to allow human review and editing of the plan/prompt in `$EDITOR`.
- **Auto-Approve (`-Y` / `--yes`):** Global non-interactive mode. Automatically approves all prompts and skips interactive pauses (implies `--yolo`).
- **Multimodal Support:** Pass images, audio, or video files directly to backends like Gemini and Qwen.
- **Image Generation (`--gen-image`):** Generate high-fidelity architectural blueprints or icons.
- **YOLO Mode (`-y`):** Unrestricted execution bypassing safety sandboxes and approval prompts.

## 2026 Model Tiers

| Backend | Easy | Mid | Hard |
| --- | --- | --- | --- |
| **Gemini** | `gemini-2.5-flash-lite` | `gemini-2.5-pro` | `gemini-3-flash-preview` |
| **Claude** | `haiku-4.5` | `sonnet-4.5` | `opus-4.5` |
| **Codex** | `gpt-5.1-codex-mini` | `gpt-5.1-codex-max` | `gpt-5.2-codex` |
| **Qwen** | `qwen3-coder` | `qwen3-coder` | `qwen3-coder` |

## Usage Examples

### Maestro Integration
`ai-run` automatically detects the current Maestro state:
```bash
ai-run "Analyze the current phase and suggest improvements"
```

### Self-Healing
```bash
ai-run --fix --backend gemini my_failing_script.py
```

### Multi-Model Debate
```bash
ai-run --debate "How should we structure the Maestro translation units?"
```

### Interactive Step
```bash
ai-run --step "Create a complex migration plan for the database"
```

### Multimodal Input
```bash
ai-run -b qwen "Identify the CSS alignment error" bug_screenshot.png
```

### Image Generation
```bash
ai-run --gen-image "Minimalist conductor baton logo" -o logo.png
```

### YOLO Mode
```bash
ai-run -y --backend codex "Refactor the entire core logic"
```

## Installation

1. Copy `ai-run` to a directory in your `PATH`.
2. Ensure it is executable: `chmod +x ai-run`.
3. Set your preferred editor: `export EDITOR=code --wait` or `export EDITOR=vi`.

## Licensing

- **Copyright:** Seppo Pakonen 2026 (C)
- **License:** GPLv3
