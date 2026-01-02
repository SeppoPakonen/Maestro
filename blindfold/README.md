# Blindfold

A tool for blind mode operations.

## Setup

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e ".[dev]"
pytest -q
```

## Invalid commands & error cookies

When blindfold receives an invalid blind command, it generates an error-cookie-id and records the error details. Invalid blind commands produce an error-cookie-id in the format "0x" + 8 lowercase hex digits, and errors are recorded under state/errors/ in JSON format.

## Feedback mode

Feedback mode allows operators to provide structured explanations for error cookies. To submit feedback:

```bash
python -m blindfold --FEEDBACK 0x........ < feedback.yaml
```

The feedback must be provided as YAML or JSON mapping (object) via stdin. The feedback is stored under `state/feedback/<cookie>.yaml`.

Example feedback.yaml:
```yaml
expectation:
  input: "user prompt"
  context: "some vars"
  process: "should do X"
  output: "expected Y"
```

## Expectation gap (missing info reporting)

When the model cannot produce the expected result because some required information is missing, it can report an "expectation gap" to indicate what information is needed. This mechanism allows the model to communicate missing information without using questions or help commands, which are not allowed in blindfold mode.

The expectation_gap should be included in the feedback payload when the model receives an error cookie, or in general feedback. The format is:

```yaml
expectation_gap:
  missing:
    - "Need database schema name for table X"
    - "Need env var FOO to locate config"
  notes: "Without these I can't produce output Y."
```

Note that questions and help are not allowed in blindfold mode; missing information should be expressed as expectation_gap instead.

## Redaction

Blindfold automatically redacts sensitive information from stored logs and feedback. Redaction rules are loaded from `<data_dir>/redaction.yaml` and applied to:

- Error ledger stdin_snippet
- Stored feedback content

The default configuration includes patterns for common sensitive data like tokens and API keys. You can customize the redaction rules by editing the configuration file.

## Garbage collection

Blindfold provides a garbage collection command to delete old error logs and feedback files:

```bash
python -m blindfold --HIDDEN gc --older-than 30d
```

This command deletes files older than the specified duration in the state directory. Supported formats:
- `Nd` for days (e.g., `30d`)
- `Nh` for hours (e.g., `12h`)
- `Nm` for minutes (e.g., `90m`)

## State database (SQLite)

Blindfold uses an SQLite database to persist session and variable data. The database is located at `<state_dir>/blindfold.sqlite3` and contains:

- `sessions`: Named working contexts with creation timestamps
- `session_vars`: Key-value variables scoped to sessions with optional type tags

## Sessions and variables (admin mode)

Admin mode provides commands to manage sessions and variables. These are for operators, not the model. Admin output is human-readable text (not YAML).

```bash
python -m blindfold --HIDDEN session list
python -m blindfold --HIDDEN session create <name>
python -m blindfold --HIDDEN session delete <name>
python -m blindfold --HIDDEN session set-active <name>
python -m blindfold --HIDDEN var set --session <name> --key <k> --value <v> [--type <t>]
python -m blindfold --HIDDEN var get --session <name> --key <k>
python -m blindfold --HIDDEN var list --session <name>
```

### Session commands

- `session list`: Lists all session names
- `session create <name>`: Creates a new session with the given name
- `session delete <name>`: Deletes the specified session and all its variables
- `session set-active <name>`: Sets the default session for blind mode (stored setting)

### Variable commands

- `var set --session <name> --key <k> --value <v> [--type <t>]`: Sets a variable in the specified session (type defaults to "string")
- `var get --session <name> --key <k>`: Gets the value of a variable from the specified session
- `var list --session <name>`: Lists all variables in the specified session

## Active session selection

Blind mode can use session variables to provide context to the model. The active session is determined by precedence:

1. Environment variable `BLINDFOLD_SESSION` (if set and non-empty)
2. Stored active session (set via `session set-active` command)
3. Default session name "default"

When a mapping matches and interface YAML is printed, the following blocks are injected:
- `session.name`: The active session name
- `fields.context.vars`: Key-value pairs from the active session

Example interface output with injected context:
```yaml
session:
  name: "my-session"
fields:
  context:
    vars:
      project: "my-project"
      environment: "production"
```

**Warning**: Variables may contain sensitive data. Pair with redaction configuration if exporting or logging.

## State database (SQLite)

Blindfold uses an SQLite database to persist session and variable data. The database is located at `<state_dir>/blindfold.sqlite3` and contains:

- `sessions`: Named working contexts with creation timestamps
- `session_vars`: Key-value variables scoped to sessions with optional type tags
- `settings`: Global settings like the active session

## Admin mode (--HIDDEN)

Admin mode provides commands for operators to inspect errors and feedback, and to add command mappings. Admin mode is for operators, not the model. Admin output is human-readable text (not YAML).

```bash
python -m blindfold --HIDDEN list-errors
python -m blindfold --HIDDEN show-error 0x....
python -m blindfold --HIDDEN list-feedback
python -m blindfold --HIDDEN show-feedback 0x....
python -m blindfold --HIDDEN add-mapping --argv "demo" --interface demo.yaml
python -m blindfold --HIDDEN gc --older-than 30d
```

### Available commands

- `list-errors`: Lists all error cookies in the state directory
- `show-error <cookie>`: Shows details of a specific error
- `list-feedback`: Lists all feedback cookies in the state directory
- `show-feedback <cookie>`: Shows details of a specific feedback
- `add-mapping --argv "<space separated tokens>" --interface <filename.yaml> [--id <id>] [--notes <text>]`: Adds a new mapping from command arguments to an interface file
- `gc --older-than <duration>`: Deletes old error logs and feedback files (older than specified duration)