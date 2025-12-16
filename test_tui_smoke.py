#!/usr/bin/env python3
"""
Smoke test for Maestro TUI
This script tests that the TUI can be started and exits correctly in smoke mode.
"""

import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def _run_smoke(smoke_seconds: float = 0.3, mc: bool = False) -> bool:
    """Execute a smoke run and return True on success."""
    flag_line = ["--mc"] if mc else []
    label = "MC shell smoke mode" if mc else "TUI smoke mode"
    print(f"\nTesting {label} with {smoke_seconds} seconds...")

    with tempfile.NamedTemporaryFile(delete=False) as marker:
        marker_path = Path(marker.name)

    marker_text = ""
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "maestro.tui",
                *(flag_line),
                "--smoke",
                "--smoke-seconds",
                str(smoke_seconds),
                "--smoke-out",
                str(marker_path),
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )

        print(f"Return code: {result.returncode}")
        print(f"STDOUT: {result.stdout}")
        print(f"STDERR: {result.stderr}")

        combined_output = result.stdout + result.stderr
        combined_output_clean = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", combined_output)
        marker_text = marker_path.read_text() if marker_path.exists() else ""

        if mc:
            rendered = ("Navigator" in combined_output_clean) or ("Sections" in combined_output_clean)
            if not rendered:
                print("❌ MC shell smoke test FAILED: Shell UI markers not seen")
                return False

        if ("MAESTRO_TUI_SMOKE_OK" in combined_output) or ("MAESTRO_TUI_SMOKE_OK" in marker_text):
            print("✅ Smoke test PASSED: Correct output found")
            return True
        else:
            print("❌ Smoke test FAILED: Expected output not found")
            print(f"Expected: MAESTRO_TUI_SMOKE_OK")
            print(f"Got combined: {combined_output}")
            return False

    except subprocess.TimeoutExpired:
        print("❌ Smoke test FAILED: Process timed out")
        return False
    except Exception as e:
        print(f"❌ Smoke test FAILED with exception: {e}")
        return False
    finally:
        marker_path.unlink(missing_ok=True)


def test_tui_smoke_mode():
    """Test that the TUI smoke mode works correctly."""
    assert _run_smoke(smoke_seconds=0.3, mc=False)


def test_tui_smoke_mode_shorter():
    """Test that the TUI smoke mode works with shorter time."""
    assert _run_smoke(smoke_seconds=0.1, mc=False)


def test_tui_mc_smoke_mode():
    """Test that the MC shell smoke path renders and exits."""
    assert _run_smoke(smoke_seconds=0.3, mc=True)


if __name__ == "__main__":
    print("Starting TUI smoke tests...\n")
    
    test1_passed = _run_smoke(smoke_seconds=0.3, mc=False)
    test2_passed = _run_smoke(smoke_seconds=0.1, mc=False)
    test3_passed = _run_smoke(smoke_seconds=0.3, mc=True)
    
    print(f"\nTest results:")
    print(f"Standard smoke test: {'PASSED' if test1_passed else 'FAILED'}")
    print(f"Short smoke test: {'PASSED' if test2_passed else 'FAILED'}")
    print(f"MC shell smoke test: {'PASSED' if test3_passed else 'FAILED'}")
    
    if test1_passed and test2_passed and test3_passed:
        print("\n🎉 All TUI smoke tests PASSED!")
        sys.exit(0)
    else:
        print("\n💥 Some TUI smoke tests FAILED!")
        sys.exit(1)
