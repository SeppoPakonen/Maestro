"""WorkGraph runner execution engine.

Provides:
- Topological task walking
- Dry-run and execution modes
- Resume capability
- Graph change detection
- Safe command execution with timeout
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from ..data.workgraph_schema import WorkGraph, Task, DefinitionOfDone
from .models import RunEvent, RunMeta, generate_run_id, compute_workgraph_hash
from .storage import (
    append_event,
    get_run_dir,
    load_events,
    load_run_meta,
    save_run_meta,
    update_run_index
)


class WorkGraphRunner:
    """Executes a WorkGraph plan with deterministic topological ordering."""

    def __init__(
        self,
        workgraph: WorkGraph,
        workgraph_dir: Path,
        dry_run: bool = True,
        max_steps: Optional[int] = None,
        only_tasks: Optional[List[str]] = None,
        skip_tasks: Optional[List[str]] = None,
        verbose: bool = False,
        very_verbose: bool = False,
        resume_run_id: Optional[str] = None,
        cmd_timeout: int = 60
    ):
        """Initialize the runner.

        Args:
            workgraph: WorkGraph to execute
            workgraph_dir: Base directory for workgraphs
            dry_run: If True, don't execute commands (default True)
            max_steps: Maximum number of tasks to execute (None = all)
            only_tasks: List of task IDs to execute (None = all)
            skip_tasks: List of task IDs to skip (None = none)
            verbose: Show detailed output
            very_verbose: Show bounded plan summary + per-task reasoning
            resume_run_id: Run ID to resume from (None = new run)
            cmd_timeout: Timeout for command execution in seconds
        """
        self.workgraph = workgraph
        self.workgraph_dir = workgraph_dir
        self.dry_run = dry_run
        self.max_steps = max_steps
        self.only_tasks = set(only_tasks or [])
        self.skip_tasks = set(skip_tasks or [])
        self.verbose = verbose
        self.very_verbose = very_verbose
        self.resume_run_id = resume_run_id
        self.cmd_timeout = cmd_timeout

        # State
        self.run_meta: Optional[RunMeta] = None
        self.run_dir: Optional[Path] = None
        self.completed_tasks: Set[str] = set()
        self.failed_tasks: Set[str] = set()
        self.skipped_tasks: Set[str] = set()
        self.task_count = 0
        # Track tasks completed in THIS execution (for resume)
        self.tasks_completed_this_run = 0
        self.tasks_failed_this_run = 0
        self.tasks_skipped_this_run = 0

    def run(self) -> Dict[str, any]:
        """Execute the WorkGraph.

        Returns:
            Summary dictionary with run results
        """
        # Initialize or resume run
        if self.resume_run_id:
            self._resume_run()
        else:
            self._start_new_run()

        # Emit RUN_STARTED event
        if not self.resume_run_id:
            self._emit_event("RUN_STARTED", {
                "workgraph_id": self.workgraph.id,
                "goal": self.workgraph.goal,
                "dry_run": self.dry_run,
                "max_steps": self.max_steps
            })

        # Build dependency graph
        task_deps = self._build_dependency_graph()

        # Topologically walk tasks
        runnable_tasks = self._get_runnable_tasks(task_deps)
        tasks_executed = 0

        while runnable_tasks and (self.max_steps is None or tasks_executed < self.max_steps):
            # Sort for deterministic ordering
            runnable_tasks = sorted(runnable_tasks, key=lambda t: t.id)

            for task in runnable_tasks:
                if self.max_steps is not None and tasks_executed >= self.max_steps:
                    break

                # Skip if already completed or in skip list
                if task.id in self.completed_tasks:
                    continue

                if task.id in self.skip_tasks:
                    self._skip_task(task)
                    continue

                # Skip if only_tasks is set and this task is not in it
                if self.only_tasks and task.id not in self.only_tasks:
                    self._skip_task(task)
                    continue

                # Execute task
                result = self._execute_task(task)
                tasks_executed += 1

                if result == "ok":
                    self.completed_tasks.add(task.id)
                    self.tasks_completed_this_run += 1
                elif result == "fail":
                    self.failed_tasks.add(task.id)
                    self.tasks_failed_this_run += 1
                    # Stop on failure
                    break
                elif result == "skipped":
                    self.skipped_tasks.add(task.id)
                    self.tasks_skipped_this_run += 1

            # Get next batch of runnable tasks
            runnable_tasks = self._get_runnable_tasks(task_deps)

        # Emit RUN_SUMMARY event
        summary = {
            "run_id": self.run_meta.run_id,
            "workgraph_id": self.workgraph.id,
            "tasks_completed": self.tasks_completed_this_run,
            "tasks_failed": self.tasks_failed_this_run,
            "tasks_skipped": self.tasks_skipped_this_run,
            "dry_run": self.dry_run
        }

        self._emit_event("RUN_SUMMARY", summary)

        # Update run meta status
        if self.failed_tasks:
            self.run_meta.status = "failed"
        elif tasks_executed >= (self.max_steps or float('inf')):
            self.run_meta.status = "stopped"
        else:
            self.run_meta.status = "completed"

        self.run_meta.completed_at = datetime.now().isoformat()
        save_run_meta(self.run_meta, self.run_dir)
        update_run_index(self.workgraph_dir, self.workgraph.id, self.run_meta)

        return summary

    def _start_new_run(self) -> None:
        """Start a new run."""
        start_time = datetime.now().isoformat()
        run_id = generate_run_id(self.workgraph.id, start_time)

        # Compute workgraph hash for change detection
        wg_json = json.dumps(self.workgraph.to_dict(), sort_keys=True)
        wg_hash = compute_workgraph_hash(wg_json)

        self.run_meta = RunMeta(
            run_id=run_id,
            workgraph_id=self.workgraph.id,
            workgraph_hash=wg_hash,
            started_at=start_time,
            dry_run=self.dry_run,
            max_steps=self.max_steps,
            only_tasks=list(self.only_tasks),
            skip_tasks=list(self.skip_tasks)
        )

        self.run_dir = get_run_dir(self.workgraph_dir, self.workgraph.id, run_id)
        self.run_dir.mkdir(parents=True, exist_ok=True)

        save_run_meta(self.run_meta, self.run_dir)
        update_run_index(self.workgraph_dir, self.workgraph.id, self.run_meta)

    def _resume_run(self) -> None:
        """Resume an existing run."""
        # Load run meta
        run_dir = get_run_dir(self.workgraph_dir, self.workgraph.id, self.resume_run_id)
        run_meta = load_run_meta(run_dir)

        if not run_meta:
            raise ValueError(f"Run not found: {self.resume_run_id}")

        # Check if workgraph has changed
        wg_json = json.dumps(self.workgraph.to_dict(), sort_keys=True)
        wg_hash = compute_workgraph_hash(wg_json)

        if wg_hash != run_meta.workgraph_hash:
            raise ValueError(
                f"WorkGraph has changed since run {self.resume_run_id} started. "
                f"Re-run 'maestro plan decompose' and 'maestro plan enact' to create a new WorkGraph."
            )

        self.run_meta = run_meta
        self.run_dir = run_dir

        # Load events to find completed tasks
        events = load_events(run_dir)
        for event in events:
            if event.event_type == "TASK_RESULT":
                task_id = event.data.get("task_id")
                result = event.data.get("result")
                if result == "ok":
                    self.completed_tasks.add(task_id)
                elif result == "fail":
                    self.failed_tasks.add(task_id)
                elif result == "skipped":
                    self.skipped_tasks.add(task_id)

        if self.verbose:
            print(f"Resuming run {self.resume_run_id}")
            print(f"  Completed tasks: {len(self.completed_tasks)}")
            print(f"  Failed tasks: {len(self.failed_tasks)}")
            print(f"  Skipped tasks: {len(self.skipped_tasks)}")

    def _build_dependency_graph(self) -> Dict[str, Set[str]]:
        """Build task dependency graph from inputs/outputs.

        Returns:
            Dictionary mapping task_id to set of task IDs it depends on
        """
        task_deps: Dict[str, Set[str]] = defaultdict(set)
        output_to_task: Dict[str, str] = {}

        # Build output map
        for phase in self.workgraph.phases:
            for task in phase.tasks:
                for output in task.outputs:
                    output_to_task[output] = task.id

        # Build dependency graph
        for phase in self.workgraph.phases:
            for task in phase.tasks:
                for input_item in task.inputs:
                    if input_item in output_to_task:
                        dep_task_id = output_to_task[input_item]
                        task_deps[task.id].add(dep_task_id)

        return task_deps

    def _get_runnable_tasks(self, task_deps: Dict[str, Set[str]]) -> List[Task]:
        """Get tasks whose dependencies are satisfied.

        Args:
            task_deps: Dependency graph

        Returns:
            List of runnable tasks
        """
        runnable = []

        for phase in self.workgraph.phases:
            for task in phase.tasks:
                # Skip if already processed
                if task.id in self.completed_tasks or task.id in self.failed_tasks or task.id in self.skipped_tasks:
                    continue

                # Check if all dependencies are satisfied
                deps = task_deps.get(task.id, set())
                if all(dep_id in self.completed_tasks for dep_id in deps):
                    runnable.append(task)

        return runnable

    def _execute_task(self, task: Task) -> str:
        """Execute a single task.

        Args:
            task: Task to execute

        Returns:
            Result: "ok", "fail", or "skipped"
        """
        # Emit TASK_STARTED event
        self._emit_event("TASK_STARTED", {
            "task_id": task.id,
            "title": task.title,
            "intent": task.intent
        })

        if self.verbose or self.very_verbose:
            print(f"\n[{task.id}] {task.title}")
            print(f"  Intent: {task.intent}")

        # In dry-run mode, just show what would be done
        if self.dry_run:
            return self._dry_run_task(task)

        # Execute task
        return self._run_task(task)

    def _dry_run_task(self, task: Task) -> str:
        """Dry-run a task (show what would be done).

        Args:
            task: Task to dry-run

        Returns:
            Result: "ok" (always succeeds in dry-run)
        """
        if self.verbose or self.very_verbose:
            print("  [DRY RUN] Would execute:")

        for dod in task.definition_of_done:
            if dod.kind == "command":
                if self.verbose or self.very_verbose:
                    print(f"    $ {dod.cmd}")
                    print(f"      Expect: {dod.expect}")
            elif dod.kind == "file":
                if self.verbose or self.very_verbose:
                    print(f"    Check file: {dod.path}")
                    print(f"      Expect: {dod.expect}")

        # Emit TASK_RESULT event
        self._emit_event("TASK_RESULT", {
            "task_id": task.id,
            "result": "ok",
            "reason": "dry-run",
            "output": ""
        })

        return "ok"

    def _run_task(self, task: Task) -> str:
        """Execute a task for real.

        Args:
            task: Task to execute

        Returns:
            Result: "ok", "fail", or "blocked"
        """
        for i, dod in enumerate(task.definition_of_done):
            if dod.kind == "command":
                result = self._execute_command(dod.cmd, dod.expect)
                if result["status"] != "ok":
                    # Emit TASK_RESULT event
                    self._emit_event("TASK_RESULT", {
                        "task_id": task.id,
                        "result": "fail",
                        "reason": result["reason"][:500],  # Bounded
                        "output": result["output"][:2000]  # Bounded
                    })
                    return "fail"
            elif dod.kind == "file":
                result = self._check_file(dod.path, dod.expect)
                if result["status"] != "ok":
                    # Emit TASK_RESULT event
                    self._emit_event("TASK_RESULT", {
                        "task_id": task.id,
                        "result": "fail",
                        "reason": result["reason"][:500],  # Bounded
                        "output": ""
                    })
                    return "fail"

        # All DoD conditions passed
        self._emit_event("TASK_RESULT", {
            "task_id": task.id,
            "result": "ok",
            "reason": "all DoD conditions satisfied",
            "output": ""
        })

        if self.verbose or self.very_verbose:
            print("  [OK] All DoD conditions satisfied")

        return "ok"

    def _execute_command(self, cmd: str, expect: str) -> Dict[str, any]:
        """Execute a command with timeout.

        Args:
            cmd: Command to execute
            expect: Expected result (e.g., "exit 0")

        Returns:
            Result dictionary with status, reason, output
        """
        if self.verbose or self.very_verbose:
            print(f"  Executing: {cmd}")

        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.cmd_timeout,
                check=False
            )

            # Check expectation
            if "exit 0" in expect.lower():
                if result.returncode == 0:
                    return {"status": "ok", "reason": "exit 0", "output": result.stdout}
                else:
                    return {
                        "status": "fail",
                        "reason": f"exit {result.returncode}",
                        "output": result.stderr or result.stdout
                    }
            else:
                # For other expectations, just check exit code
                if result.returncode == 0:
                    return {"status": "ok", "reason": "success", "output": result.stdout}
                else:
                    return {
                        "status": "fail",
                        "reason": f"exit {result.returncode}",
                        "output": result.stderr or result.stdout
                    }

        except subprocess.TimeoutExpired:
            return {
                "status": "fail",
                "reason": f"command timeout ({self.cmd_timeout}s)",
                "output": ""
            }
        except Exception as e:
            return {
                "status": "fail",
                "reason": f"execution error: {str(e)}",
                "output": ""
            }

    def _check_file(self, path: str, expect: str) -> Dict[str, any]:
        """Check a file condition.

        Args:
            path: File path to check
            expect: Expected condition (e.g., "exists")

        Returns:
            Result dictionary with status, reason
        """
        file_path = Path(path)

        if "exists" in expect.lower():
            if file_path.exists():
                return {"status": "ok", "reason": "file exists"}
            else:
                return {"status": "fail", "reason": f"file not found: {path}"}
        else:
            # For other expectations, just check existence
            if file_path.exists():
                return {"status": "ok", "reason": "file exists"}
            else:
                return {"status": "fail", "reason": f"file not found: {path}"}

    def _skip_task(self, task: Task) -> None:
        """Skip a task.

        Args:
            task: Task to skip
        """
        self._emit_event("TASK_SKIPPED", {
            "task_id": task.id,
            "title": task.title
        })
        self.skipped_tasks.add(task.id)
        self.tasks_skipped_this_run += 1

        if self.verbose or self.very_verbose:
            print(f"\n[{task.id}] {task.title}")
            print("  [SKIPPED]")

    def _emit_event(self, event_type: str, data: Dict[str, any]) -> None:
        """Emit an event to the run record.

        Args:
            event_type: Type of event
            data: Event data
        """
        event = RunEvent(
            event_type=event_type,
            timestamp=datetime.now().isoformat(),
            data=data
        )
        append_event(event, self.run_dir)
