# EX-12: Micro "Game Loop" (Text Adventure) — Runbook→Workflow→Plan→Minimal Code

**Scope**: Runbook-first game development (minimal text adventure)
**Build System**: None (single Python file)
**Languages**: Python 3.11+
**Outcome**: Model a tiny text adventure game loop as runbook, extract workflow showing interface as "world script", implement minimal playable code

---

## Scenario Summary

Game designer wants to create a minimal text adventure with basic commands (look, go, take). They start with a runbook modeling the player experience and world state transitions, extract a workflow showing the game loop as the interface layer (not decomposing into "game engine"), then implement the minimal code.

This demonstrates **interface layer is not always CLI/TUI/GUI** — it can be a game world script or loop.

---

## Preconditions

- Empty directory or new project
- Python 3.11+ available
- Maestro initialized (or will initialize)

---

## Minimal Project Skeleton (Final State)

```
text-adventure/
├── docs/
│   └── maestro/
│       ├── runbooks/
│       │   └── text-adventure-game.json
│       ├── workflows/
│       │   └── game-loop-workflow.json
│       └── tracks/
│           └── track-001.json
└── adventure.py
```

**adventure.py** (final implementation):
```python
#!/usr/bin/env python3

# Minimal text adventure: 3 rooms, 1 item
rooms = {
    'start': {
        'desc': 'You are in a small cottage.',
        'exits': {'north': 'forest'},
        'items': ['key']
    },
    'forest': {
        'desc': 'You are in a dark forest.',
        'exits': {'south': 'start', 'east': 'cave'},
        'items': []
    },
    'cave': {
        'desc': 'You are in a damp cave. Victory!',
        'exits': {'west': 'forest'},
        'items': []
    }
}

current_room = 'start'
inventory = []

def cmd_look():
    room = rooms[current_room]
    print(room['desc'])
    if room['items']:
        print(f"You see: {', '.join(room['items'])}")
    print(f"Exits: {', '.join(room['exits'].keys())}")

def cmd_go(direction):
    global current_room
    room = rooms[current_room]
    if direction in room['exits']:
        current_room = room['exits'][direction]
        print(f"You go {direction}.")
        cmd_look()
    else:
        print("You can't go that way.")

def cmd_take(item):
    room = rooms[current_room]
    if item in room['items']:
        room['items'].remove(item)
        inventory.append(item)
        print(f"You take the {item}.")
    else:
        print(f"There is no {item} here.")

def cmd_inventory():
    if inventory:
        print(f"You are carrying: {', '.join(inventory)}")
    else:
        print("You are carrying nothing.")

def main():
    print("=== Micro Adventure ===")
    cmd_look()

    while True:
        try:
            user_input = input("\n> ").strip().lower()
            if not user_input:
                continue

            parts = user_input.split()
            command = parts[0]

            if command == 'quit':
                print("Goodbye!")
                break
            elif command == 'look':
                cmd_look()
            elif command == 'go' and len(parts) > 1:
                cmd_go(parts[1])
            elif command == 'take' and len(parts) > 1:
                cmd_take(parts[1])
            elif command == 'inventory' or command == 'i':
                cmd_inventory()
            else:
                print("Unknown command. Try: look, go <direction>, take <item>, inventory, quit")

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break

if __name__ == '__main__':
    main()
```

---

## Runbook Steps

### Step 1: Initialize Maestro

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro init` | Create repo truth | `./docs/maestro/**` created |

### Step 2: Create Runbook for Game Experience

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro runbook add --title "Text Adventure Game Loop" --scope product --tag game --tag greenfield` | Model game experience | Runbook `text-adventure-game-loop.json` created |

### Step 3: Add Runbook Steps (Player Journey)

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro runbook step-add text-adventure-game-loop --actor manager --action "Define goal: minimal playable text adventure" --expected "Goal documented"` | Manager intent | Step 1 added |
| `maestro runbook step-add text-adventure-game-loop --actor user --action "Run: python adventure.py" --expected "Game starts, shows starting room description"` | User intent (start) | Step 2 added |
| `maestro runbook step-add text-adventure-game-loop --actor user --action "Type: look" --expected "Displays room description and available exits"` | User intent (look) | Step 3 added |
| `maestro runbook step-add text-adventure-game-loop --actor user --action "Type: go north" --expected "Player moves to forest, new room description shown"` | User intent (move) | Step 4 added |
| `maestro runbook step-add text-adventure-game-loop --actor user --action "Type: take key" --expected "Key added to inventory"` | User intent (take item) | Step 5 added |
| `maestro runbook step-add text-adventure-game-loop --actor user --action "Type: inventory" --expected "Shows: 'You are carrying: key'"` | User intent (check inventory) | Step 6 added |
| `maestro runbook step-add text-adventure-game-loop --actor system --action "Parse user command (look/go/take), update world state" --expected "Command processed, state updated"` | Interface layer (game loop) | Step 7 added |
| `maestro runbook step-add text-adventure-game-loop --actor ai --action "Implement adventure.py with rooms dict and command parser" --expected "Game loop functional"` | Code layer | Step 8 added |

### Step 4: Export Runbook

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro runbook export text-adventure-game-loop --format md` | Review runbook | Markdown printed |

---

## Workflow Extraction (Runbook → Workflow)

### Step 5: Create Workflow from Runbook

| Command | Intent | Expected |
|---------|--------|----------|
| `TODO_CMD: maestro workflow init game-loop-workflow --from-runbook text-adventure-game-loop` | Extract workflow | Workflow JSON created |

### Step 6: Add Workflow Nodes (Layered — Game Loop as Interface)

| Command | Intent | Expected |
|---------|--------|----------|
| `TODO_CMD: maestro workflow node add game-loop-workflow --layer manager_intent --label "Goal: minimal playable adventure"` | Manager intent | Node added |
| `TODO_CMD: maestro workflow node add game-loop-workflow --layer user_intent --label "Player explores rooms, takes items"` | User intent | Node added |
| `TODO_CMD: maestro workflow node add game-loop-workflow --layer interface --label "Game loop: parse commands, update world state"` | Interface (world script) | Node added |
| `TODO_CMD: maestro workflow node add game-loop-workflow --layer code --label "adventure.py: rooms dict + command parser"` | Code | Node added |

**Key Point:** Interface layer is the game loop / world script, not a traditional CLI.

### Step 7: Validate Workflow

| Command | Intent | Expected |
|---------|--------|----------|
| `TODO_CMD: maestro workflow validate game-loop-workflow` | Check graph | Validation passes |

---

## Plan Creation (Workflow → Track/Phase/Task)

### Step 8: Create Track

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro track add "Sprint 1: Text Adventure MVP" --start 2025-01-01` | Create work track | Track `track-001` created |

### Step 9: Create Phase

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro phase add track-001 "P1: Implement Game Loop"` | Add phase | Phase `phase-001` created |

### Step 10: Create Task

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro task add phase-001 "Implement adventure.py with rooms and commands"` | Add task | Task `task-001` created |

---

## Work Execution Loop (Plan → Implementation)

### Step 11: Start Work Session

| Command | Intent | Expected |
|---------|--------|----------|
| `maestro work task task-001` | Start work with runbook context | Work session created, AI has runbook/workflow context |

### Step 12: AI Implements Code

AI generates `adventure.py` based on runbook steps:
- Rooms dict with descriptions and exits
- Command parser for look/go/take/inventory
- Game loop with input prompt

### Step 13: Test Implementation

| Command | Intent | Expected |
|---------|--------|----------|
| `python adventure.py` | Start game | Game starts, shows starting room |

**Sample play session**:
```
=== Micro Adventure ===
You are in a small cottage.
You see: key
Exits: north

> look
You are in a small cottage.
You see: key
Exits: north

> take key
You take the key.

> go north
You go north.
You are in a dark forest.
Exits: south, east

> go east
You go east.
You are in a damp cave. Victory!
Exits: west

> quit
Goodbye!
```

### Step 14: Complete Task

| Command | Intent | Expected |
|---------|--------|----------|
| `TODO_CMD: maestro task complete task-001` | Mark task done | Task status → completed |

---

## AI Perspective (Heuristic)

**What AI notices:**
- Runbook steps show command-response pattern (user types "look" → system shows description)
- Interface layer is a "world state machine" (not CLI argument parsing)
- User steps suggest dict-based rooms with connections and items

**What AI tries:**
- Generate minimal rooms dict with 2-3 rooms
- Implement simple command parser (split input, match verbs)
- Avoid over-engineering (no save/load, no combat, no NPCs unless in runbook)

**Where AI tends to hallucinate:**
- May add complex parser (synonyms, multi-word commands) when simple is sufficient
- May generate large room maps when runbook shows only 2-3 rooms
- May add features like health/combat when runbook only mentions look/go/take

---

## Outcomes

### Outcome A: Success Path

**Result:** `adventure.py` implemented and playable

**Artifacts:**
- Runbook: `./docs/maestro/runbooks/text-adventure-game-loop.json`
- Workflow: `./docs/maestro/workflows/game-loop-workflow.json`
- Task: `./docs/maestro/tasks/task-001.json` (status: completed)
- Code: `adventure.py` (playable)

**Play session works:**
- Commands: look, go <dir>, take <item>, inventory, quit
- World state updates correctly

### Outcome B: Failure — Missing Command Parsing

**Result:** First implementation forgets to handle "go" command

**Recovery:**
1. Test reveals "go north" → "Unknown command"
2. Create issue: `TODO_CMD: maestro issues add --type bug --desc "Missing 'go' command implementation"`
3. AI fixes command parser
4. Retest succeeds

### Outcome C: Extension — Add More Rooms

**Result:** After MVP works, team wants to add more rooms

**Flow:**
1. Revise runbook: add steps for new rooms (dungeon, tower)
2. Update workflow with new interface nodes
3. Create task: "Add dungeon and tower rooms"
4. Extend `rooms` dict in `adventure.py`

---

## CLI Gaps / TODOs

```yaml
cli_gaps:
  - "TODO_CMD: maestro workflow init <name> --from-runbook <id>"
  - "TODO_CMD: maestro workflow node add <id> --layer interface --label <text>"
  - "TODO_CMD: maestro workflow validate <id>"
  - "TODO_CMD: maestro task complete <id>"
  - "TODO_CMD: maestro issues add --type bug --desc <text>"
```

---

## Trace Block (YAML)

```yaml
trace:
  - user: "maestro runbook add --title 'Text Adventure Game Loop' --scope product --tag game"
    intent: "Model text adventure experience as runbook"
    gates: ["REPOCONF_GATE"]
    stores_write: ["REPO_TRUTH_DOCS_MAESTRO"]
    internal: ["UNKNOWN"]
    cli_confidence: "high"

  - user: "maestro runbook step-add text-adventure-game-loop --actor user --action 'Type: look' ..."
    intent: "Document player command and expected response"
    gates: ["REPOCONF_GATE"]
    stores_write: ["REPO_TRUTH_DOCS_MAESTRO"]
    internal: ["UNKNOWN"]
    cli_confidence: "high"

  - user: "maestro workflow init game-loop-workflow --from-runbook text-adventure-game-loop"
    intent: "Extract workflow showing game loop as interface layer"
    gates: ["REPOCONF_GATE"]
    stores_write: ["REPO_TRUTH_DOCS_MAESTRO"]
    internal: ["UNKNOWN"]
    cli_confidence: "low"  # TODO_CMD

  - user: "maestro work task task-001"
    intent: "Start work session with runbook/workflow context"
    gates: ["REPOCONF_GATE"]
    stores_write: ["REPO_TRUTH_DOCS_MAESTRO", "IPC_MAILBOX"]
    internal: ["UNKNOWN"]
    cli_confidence: "medium"
```

---

**Related:** Game development, world scripting, interface-as-loop pattern
**Status:** Proposed
