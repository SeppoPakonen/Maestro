# ai-run

`ai-run` is a smart command-line wrapper and interpreter for AI prompts. It supports multiple backends and automatically maps task difficulty to the appropriate 2026 model tiers.

## Features

- **Shebang Support:** Use `#!/usr/bin/env ai-run` to create executable prompt files.
- **Backend Selection:** Easily switch between Gemini, Codex, Claude, and Qwen.
- **Difficulty Mapping:** Automatically or manually select model tiers (easy, mid, hard).
- **YOLO Mode (`-y` / `--yolo`):** Unrestricted execution mode that bypasses safety sandboxes and approval prompts.
- **Auto-Evaluation:** Uses AI to assess the difficulty of your prompt and selects the best model for the task.
- **Persistent Memory:** Keeps track of all executions and history in `~/.maestro/ai-run/`.
- **Status Check:** Verify backend availability and estimated quota.

## 2026 Model Tiers

| Backend | Easy | Mid | Hard |
| --- | --- | --- | --- |
| **Gemini** | `gemini-2.5-flash-lite` | `gemini-2.5-pro` | `gemini-3-flash-preview` |
| **Claude** | `haiku-4.5` | `sonnet-4.5` | `opus-4.5` |
| **Codex** | `gpt-5.1-codex-mini` | `gpt-5.1-codex-max` | `gpt-5.2-codex` |
| **Qwen** | `qwen3-coder` | `qwen3-coder` | `qwen3-coder` |

*Note: Qwen also supports `-d coder` and `-d vision` (using `qwen3-vl`) for specific model variants.*

## Installation

1. Copy `ai-run` to a directory in your `PATH` (e.g., `/usr/local/bin/` or `~/bin/`).
2. Ensure it is executable: `chmod +x ai-run`.

## Usage

### Simple Prompt
```bash
ai-run "Explain quantum entanglement"
```

### YOLO Mode (Unrestricted)
```bash
ai-run -y "Analyze system logs and fix any critical issues found"
```

### Select Backend and Difficulty
```bash
ai-run -b claude -d hard "Write a complex rust macro"
```

### Auto-Evaluate Difficulty
```bash
ai-run -ed "Refactor this 1000-line legacy C++ file"
```

### As an Interpreter (Shebang)
Create a file named `task.ai`:
```bash
#!/usr/bin/env ai-run
# -y -b gemini -d hard
Please analyze the performance bottlenecks in the following code:
...
```
Then run it:
```bash
chmod +x task.ai
./task.ai
```

### Check Status
```bash
ai-run --status
```

## Configuration & History

- **History:** Stored in `~/.maestro/ai-run/history.jsonl`.
- **Requirements:** Requires the respective backend CLI tools (`gemini`, `claude`, `codex`, `qwen`) to be installed and configured in your environment.

## Licensing

- **Copyright:** Seppo Pakonen 2026 (C)
- **License:** GPLv3