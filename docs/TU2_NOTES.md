# TU2 Incremental Builder Notes

This system implements an incremental translation unit (TU) builder with caching:

## Components

- `FileHasher`: Manages SHA-256 hashes of files, persisted to JSON
- `ASTCache`: Stores/retrieves AST documents and metadata with optional compression
- `TUBuilder`: Orchestrates building with incremental caching based on file hashes

## Cache Layout

By default, caches to `.maestro/tu/cache/` with subdirs:
- `ast/`: Serialized AST documents (`.json` or `.json.gz`)
- `meta/`: Metadata JSON files (`.json`)
- `file_hashes.json`: Mapping of file paths to hashes

## Testing

Run tests with: `pytest tests/test_tu_builder.py`

## Notes

- Libclang parsing is optional; custom parsers can be implemented
- Delete the cache directory to reset and force re-parsing
- The builder only re-parses files whose content hash has changed