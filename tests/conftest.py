import os
import tempfile
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def ensure_valid_cwd():
    try:
        os.getcwd()
    except FileNotFoundError:
        os.chdir(Path(__file__).resolve().parents[1])
    yield


@pytest.fixture(autouse=True)
def isolate_docs_root(tmp_path):
    """Isolate docs root to prevent tests from polluting repo with locks/logs/state.

    Sets MAESTRO_DOCS_ROOT to a temporary directory for the duration of each test.
    This ensures locks, AI logs, and state files are created in the temp directory.
    """
    # Create a temp directory for this test's docs root
    test_docs_root = tmp_path / "test_docs_root"
    test_docs_root.mkdir(exist_ok=True)

    # Set the environment variable
    old_value = os.environ.get('MAESTRO_DOCS_ROOT')
    os.environ['MAESTRO_DOCS_ROOT'] = str(test_docs_root)

    yield test_docs_root

    # Restore the original value
    if old_value is not None:
        os.environ['MAESTRO_DOCS_ROOT'] = old_value
    else:
        os.environ.pop('MAESTRO_DOCS_ROOT', None)
