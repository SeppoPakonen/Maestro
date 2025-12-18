from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict, Optional, Union


class FileHasher:
    """Manages SHA-256 hashes for files and persists them to JSON."""

    def __init__(self, json_path: Union[Path, str]):
        self.json_path = Path(json_path)
        self.mapping: Dict[str, str] = {}

        # Load existing mapping if file exists
        if self.json_path.exists():
            try:
                with open(self.json_path, 'r') as f:
                    self.mapping = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                # Tolerate empty files
                self.mapping = {}

    def hash_file(self, path: Union[Path, str]) -> str:
        """Compute SHA-256 hash of a file."""
        abs_path = str(Path(path).resolve())
        with open(abs_path, 'rb') as f:
            file_bytes = f.read()
        return hashlib.sha256(file_bytes).hexdigest()

    def get(self, path: Union[Path, str]) -> Optional[str]:
        """Get the stored hash for a file."""
        abs_path = str(Path(path).resolve())
        return self.mapping.get(abs_path)

    def update(self, path: Union[Path, str], digest: str) -> None:
        """Update the stored hash for a file."""
        abs_path = str(Path(path).resolve())
        self.mapping[abs_path] = digest

    def persist(self) -> None:
        """Write the mapping to disk."""
        self.json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.json_path, 'w') as f:
            json.dump(self.mapping, f)
