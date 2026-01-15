"""
Helpers for libclang integration (include discovery, default flags, safe cursor helpers).
"""

from __future__ import annotations

import subprocess
from functools import lru_cache
from typing import Iterable, List, Optional, Sequence

from .errors import ParserUnavailableError


@lru_cache(maxsize=1)
def get_builtin_include_paths() -> List[str]:
    """
    Detect clang builtin include search paths by parsing:
        clang -E -x c++ - -v </dev/null

    Returns a list of include directories. If detection fails, returns [].
    """
    try:
        proc = subprocess.run(
            ["clang", "-E", "-x", "c++", "-", "-v"],
            input=b"",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except FileNotFoundError as exc:
        raise ParserUnavailableError("clang is not installed on PATH") from exc

    text = proc.stderr.decode("utf-8", errors="ignore") + proc.stdout.decode("utf-8", errors="ignore")
    lines = text.splitlines()
    includes: List[str] = []
    in_block = False
    for line in lines:
        line = line.strip()
        if "search starts here" in line:
            in_block = True
            continue
        if in_block and line.startswith("End of search list"):
            break
        if in_block:
            # Lines typically start with a space then a path
            path = line.strip()
            if path:
                includes.append(path)
    return includes


# Backward-compatible alias
def get_clang_builtin_includes() -> List[str]:
    return get_builtin_include_paths()


def get_default_compile_flags(language: str = "c++", extra: Optional[Iterable[str]] = None) -> List[str]:
    """
    Provide a set of sensible default flags for parsing/completion.
    """
    if language.lower() in ("c", "c89", "c99", "c11"):
        flags: List[str] = ["-x", "c"]
    else:
        flags = ["-x", "c++", "-std=c++17"]
    for inc in get_builtin_include_paths():
        flags.extend(["-I", inc])
    if extra:
        flags.extend(list(extra))
    return flags


def filter_clang_flags(flags: List[str]) -> List[str]:
    """
    Filter out flags that are incompatible with libclang or unnecessary for AST generation.
    """
    filtered = []
    skip_next = False
    
    # Incompatible or unnecessary flag prefixes
    exclude_prefixes = (
        "-O",      # Optimization
        "-g",      # Debug info
        "-M",      # Dependency generation
        "-W",      # Warnings (keep some if needed, but often noisy)
        "-fstack-",
        "-fomit-frame-pointer",
        "-mtune=",
        "-march=",
    )
    
    # Linker flags to remove
    linker_prefixes = (
        "-l",
        "-L",
        "-Wl,",
    )

    for i, flag in enumerate(flags):
        if skip_next:
            skip_next = False
            continue
            
        # Skip flags that take an argument we don't want
        if flag in ("-o", "--output"):
            skip_next = True
            continue
            
        if flag.startswith(exclude_prefixes):
            # Keep some warnings if explicitly desired, but generally skip
            continue
            
        if flag.startswith(linker_prefixes):
            continue
            
        # Keep defines, includes, and language standards
        filtered.append(flag)
        
    return filtered


def safe_get_usr(cursor) -> Optional[str]:
    try:
        return cursor.get_usr() or None
    except Exception:
        return None


def safe_get_type_spelling(cursor) -> Optional[str]:
    try:
        if cursor.type is not None:
            return cursor.type.spelling or None
    except Exception:
        return None
    return None


def is_reference_cursor(cursor) -> bool:
    """
    Heuristic to decide if a cursor represents a reference to another symbol.
    """
    try:
        from clang.cindex import CursorKind  # type: ignore

        return cursor.kind in {
            CursorKind.DECL_REF_EXPR,
            CursorKind.MEMBER_REF_EXPR,
            CursorKind.TYPE_REF,
            CursorKind.MEMBER_REF,
            CursorKind.NAMESPACE_REF,
            CursorKind.OVERLOADED_DECL_REF,
            CursorKind.CALL_EXPR,
        }
    except Exception:
        return False
