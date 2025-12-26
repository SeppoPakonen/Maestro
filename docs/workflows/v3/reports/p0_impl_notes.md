# P0 Implementation Notes (v3)

- CLI entrypoints: `maestro/main.py`, `maestro/modules/cli_parser.py`
- Repo resolve/write paths: `maestro/commands/repo.py`, `maestro/repo/scanner.py`
- Make/build command: `maestro/commands/make.py`
- TU command: `maestro/commands/tu.py`
- Convert command: `maestro/commands/convert.py`
- Work sessions + breadcrumbs: `maestro/work_session.py`, `maestro/breadcrumb.py`, `maestro/commands/work_session.py`
- Discuss router + JSON contract: `maestro/ai/discuss_router.py`, `maestro/commands/discuss.py`
- Legacy session handlers: `maestro/modules/command_handlers.py`
