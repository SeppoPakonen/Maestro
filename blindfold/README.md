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