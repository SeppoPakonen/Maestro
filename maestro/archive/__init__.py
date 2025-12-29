"""Archive lifecycle management for runbooks and workflows."""
from __future__ import annotations

from maestro.archive.runbook_archive import (
    archive_runbook_json,
    archive_runbook_markdown,
    list_archived_runbooks,
    restore_runbook_json,
    restore_runbook_markdown,
)
from maestro.archive.runbook_archive import ArchiveError as RunbookArchiveError
from maestro.archive.runbook_archive import RestoreError as RunbookRestoreError
from maestro.archive.runbook_archive import find_archive_entry as find_runbook_archive
from maestro.archive.storage import (
    ArchiveEntry,
    ArchiveIndex,
    generate_archive_id,
    get_timestamp_folder,
    load_archive_index,
    save_archive_index,
)
from maestro.archive.workflow_archive import (
    archive_workflow,
    list_active_workflows,
    list_archived_workflows,
    restore_workflow,
)
from maestro.archive.workflow_archive import ArchiveError as WorkflowArchiveError
from maestro.archive.workflow_archive import RestoreError as WorkflowRestoreError
from maestro.archive.workflow_archive import (
    find_archive_entry as find_workflow_archive,
)

# Export unified error classes
ArchiveError = RunbookArchiveError
RestoreError = RunbookRestoreError

__all__ = [
    "ArchiveEntry",
    "ArchiveIndex",
    "ArchiveError",
    "RestoreError",
    "RunbookArchiveError",
    "RunbookRestoreError",
    "WorkflowArchiveError",
    "WorkflowRestoreError",
    "archive_runbook_json",
    "archive_runbook_markdown",
    "archive_workflow",
    "find_runbook_archive",
    "find_workflow_archive",
    "generate_archive_id",
    "get_timestamp_folder",
    "list_active_workflows",
    "list_archived_runbooks",
    "list_archived_workflows",
    "load_archive_index",
    "restore_runbook_json",
    "restore_runbook_markdown",
    "restore_workflow",
    "save_archive_index",
]
