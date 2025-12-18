from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import json
import gzip

from .ast_nodes import ASTDocument
from .serializer import ASTSerializer


@dataclass
class CacheMetadata:
    """Metadata for cached AST documents."""

    source_path: str
    file_hash: str
    dependencies: Optional[List[str]] = None
    compile_flags: Optional[List[str]] = None

    def to_dict(self) -> dict:
        result = {
            'source_path': self.source_path,
            'file_hash': self.file_hash,
        }
        if self.dependencies is not None:
            result['dependencies'] = self.dependencies
        if self.compile_flags is not None:
            result['compile_flags'] = self.compile_flags
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'CacheMetadata':
        return cls(
            source_path=data['source_path'],
            file_hash=data['file_hash'],
            dependencies=data.get('dependencies'),
            compile_flags=data.get('compile_flags'),
        )


class ASTCache:
    """Cache for AST documents with associated metadata."""

    def __init__(self, base_dir: Union[Path, str]):
        self.base_dir = Path(base_dir)
        self.ast_dir = self.base_dir / 'ast'
        self.meta_dir = self.base_dir / 'meta'

        # Create directories if they don't exist
        self.ast_dir.mkdir(parents=True, exist_ok=True)
        self.meta_dir.mkdir(parents=True, exist_ok=True)

    def store(self, document: ASTDocument, metadata: CacheMetadata, *, compress: bool = False) -> None:
        """Store the AST document and its metadata."""
        file_hash = metadata.file_hash
        ast_path = self.ast_dir / f"{file_hash}.json"
        if compress:
            ast_path = ast_path.with_suffix(".json.gz")
        meta_path = self.meta_dir / f"{file_hash}.json"

        # Write AST document
        serialized_ast = ASTSerializer.to_bytes(document, compress=compress)
        with open(ast_path, 'wb') as f:
            f.write(serialized_ast)

        # Write metadata
        with open(meta_path, 'w') as f:
            json.dump(metadata.to_dict(), f)

    def load(self, file_hash: str) -> Tuple[ASTDocument, CacheMetadata]:
        """Load an AST document and its metadata by file hash."""
        ast_path = self.ast_dir / f"{file_hash}.json"
        meta_path = self.meta_dir / f"{file_hash}.json"

        # Check for compressed version if uncompressed not found
        if not ast_path.exists():
            ast_path = ast_path.with_suffix(".json.gz")

        if not ast_path.exists():
            raise FileNotFoundError(f"AST cache not found for hash {file_hash}")

        # Read metadata
        with open(meta_path, 'r') as f:
            metadata = CacheMetadata.from_dict(json.load(f))

        # Read AST document
        with open(ast_path, 'rb') as f:
            data = f.read()

        # Determine whether to decompress based on file extension
        is_compressed = ast_path.suffix == '.gz'
        if is_compressed:
            # gzip.decompress returns plain bytes; serializer should not decompress again
            decompressed_data = gzip.decompress(data)
            document = ASTSerializer.from_bytes(decompressed_data, compress=False)
        else:
            # Deserialize normally
            document = ASTSerializer.from_bytes(data, compress=is_compressed)

        return document, metadata

    def load_if_present(self, file_hash: str) -> Optional[Tuple[ASTDocument, CacheMetadata]]:
        """Load an AST document and its metadata if they exist, else return None."""
        try:
            return self.load(file_hash)
        except FileNotFoundError:
            return None
