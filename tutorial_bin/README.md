# Maestro Automated Tutorial Runners

This directory contains a suite of automated execution scripts that guide an AI agent through Maestro tutorials.

## Architecture

- **`maestro-tutorial-helper`**: A Python utility that provides sandbox setup, state discovery, and validation logic.
- **`run-tutorial-*`**: `ai-run` scripts that serve as the "brain" for the automated execution. Each script guides an AI agent through a specific tutorial.

## Usage

To run a tutorial automatically:

```bash
./tutorial_bin/run-tutorial-intro
```

This will:
1. Clone a random open-source repository into `~/.maestro/tutorials/<tutorial-name>/`.
2. Initialize Maestro in that sandbox.
3. Create a Maestro Track to track tutorial progress.
4. Execute each step of the tutorial using AI.
5. Validate outcomes and self-heal if necessary.

## State Management

Progress is tracked using Maestro's internal **Track/Phase/Task** system. If a tutorial is interrupted, running the script again will:
1. Detect the existing sandbox.
2. Check the Maestro Track for completed tasks.
3. Resume execution from the first incomplete task.

## Resetting a Tutorial

To start a tutorial from scratch, delete the corresponding sandbox and Maestro track:

```bash
rm -rf ~/.maestro/tutorials/<tutorial-name>/
# Then manually remove the track using maestro track rm if necessary, 
# or just delete the sandbox and the script will create a new one.
```

## Requirements

- `ai-run` must be in your `PATH`.
- Python 3.12+
- Internet access (for cloning GitHub repositories).

## License

GPLv3
