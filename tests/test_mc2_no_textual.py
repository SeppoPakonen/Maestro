"""
Ensure MC2 entry does not import Textual when running in mc2 mode.
"""

import os
import subprocess
import sys
import textwrap
from pathlib import Path


def test_mc2_runs_without_textual_import():
    repo_root = Path(__file__).resolve().parents[1]
    script = textwrap.dedent(
        """
        import builtins
        import sys

        real_import = builtins.__import__

        def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name.startswith("textual"):
                raise ImportError("blocked textual import")
            return real_import(name, globals, locals, fromlist, level)

        builtins.__import__ = guarded_import

        sys.argv = [
            "-m",
            "maestro.tui",
            "--mc2",
            "--smoke",
            "--smoke-seconds",
            "0.1",
        ]

        import maestro.tui.__main__ as main_mod
        main_mod.main()
        """
    )

    env = os.environ.copy()
    pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = str(repo_root) if not pythonpath else f"{repo_root}{os.pathsep}{pythonpath}"

    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=5,
        env=env,
    )

    output = result.stdout + result.stderr
    assert result.returncode == 0, f"MC2 entry failed: {output}"
    assert "MAESTRO_TUI_SMOKE_OK" in output, f"Smoke marker missing: {output}"
