"""
Make screen for the Textual TUI (option 1).
"""
from __future__ import annotations

import os
from textual import on
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Static
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    RichLog,
    Static,
)

from maestro.tui.utils import ErrorModal, ErrorNormalizer
from maestro.ui_facade.make import run_make_command


class MakeScreen(Static):
    """Run Maestro make commands from the Textual UI."""

    BINDINGS = [
        ("enter", "run_command", "Run"),
        ("m", "run_methods", "List methods"),
        ("d", "run_detect", "Detect"),
    ]

    def compose(self) -> ComposeResult:
        header = Header()

        buttons = Horizontal(
            Button("Run", id="make-run", variant="primary"),
            Button("Methods", id="make-methods", variant="default"),
            Button("Detect", id="make-detect", variant="success"),
            id="make-buttons",
        )

        controls = Vertical(
            Label("Make command:", id="make-label"),
            Input(placeholder="e.g. methods | config detect | build MyPkg", id="make-input"),
            buttons,
            id="make-controls",
        )

        output = Vertical(
            Label("Output", id="make-output-label"),
            RichLog(id="make-output-log", wrap=True),
            id="make-output-pane",
        )

        status = Static("", id="make-status")

        body = Container(
            controls,
            output,
            status,
            id="make-screen",
        )

        footer = Footer()

        yield header
        yield body
        yield footer

    def _append_output(self, text: str) -> None:
        log = self.query_one("#make-output-log", RichLog)
        if text:
            for line in text.splitlines():
                log.write(line)

    def _set_status(self, message: str) -> None:
        status = self.query_one("#make-status", Static)
        status.update(message)

    def _run_command_line(self, command_line: str) -> None:
        try:
            status_code, output = run_make_command(command_line, cwd=os.getcwd())
            self._append_output(output or "(no output)")
            status_text = "OK" if status_code == 0 else f"Exit {status_code}"
            self._set_status(f"{status_text}: {command_line or '(empty)'}")
        except Exception as exc:
            error_msg = ErrorNormalizer.normalize_exception(exc, "running make command")
            self.app.push_screen(ErrorModal(error_msg))
            self._set_status(error_msg.message)

    @on(Button.Pressed, "#make-run")
    def _on_run(self, _: Button.Pressed) -> None:
        command_line = self.query_one("#make-input", Input).value.strip()
        self._run_command_line(command_line)

    @on(Button.Pressed, "#make-methods")
    def _on_methods(self, _: Button.Pressed) -> None:
        self.query_one("#make-input", Input).value = "methods"
        self._run_command_line("methods")

    @on(Button.Pressed, "#make-detect")
    def _on_detect(self, _: Button.Pressed) -> None:
        self.query_one("#make-input", Input).value = "config detect"
        self._run_command_line("config detect")

    @on(Input.Submitted, "#make-input")
    def _on_input_submitted(self, event: Input.Submitted) -> None:
        self._run_command_line(event.value.strip())

    def action_run_command(self) -> None:
        command_line = self.query_one("#make-input", Input).value.strip()
        self._run_command_line(command_line)

    def action_run_methods(self) -> None:
        self.query_one("#make-input", Input).value = "methods"
        self._run_command_line("methods")

    def action_run_detect(self) -> None:
        self.query_one("#make-input", Input).value = "config detect"
        self._run_command_line("config detect")
