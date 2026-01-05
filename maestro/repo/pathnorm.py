"""Path normalization helpers for repo model portability."""
from __future__ import annotations

from dataclasses import dataclass
import os
import re
from pathlib import Path
from typing import Iterable, Tuple


_WINDOWS_DRIVE_RE = re.compile(r'^([a-zA-Z]):(.*)$')
_WSL_MNT_RE = re.compile(r'^/mnt/([a-zA-Z])(?:/(.*))?$')
_WSL_DRIVE_RE = re.compile(r'^/([a-zA-Z])/(.*)$')


@dataclass(frozen=True)
class ParsedPath:
    kind: str
    root: str
    parts: Tuple[str, ...]
    casefold: bool = False


def _collapse_parts(parts: Iterable[str]) -> Tuple[str, ...]:
    collapsed = []
    for part in parts:
        if part in ("", "."):
            continue
        if part == "..":
            if collapsed and collapsed[-1] != "..":
                collapsed.pop()
            else:
                collapsed.append(part)
            continue
        collapsed.append(part)
    return tuple(collapsed)


def _normalize_slashes(path_str: str) -> str:
    return path_str.replace("\\", "/")


def parse_path(path: str) -> ParsedPath:
    """Parse a path into normalized components without touching the filesystem."""
    if path is None:
        return ParsedPath("relative", "", tuple(), False)
    raw = str(path).strip()
    if not raw:
        return ParsedPath("relative", "", tuple(), False)

    raw = _normalize_slashes(raw)

    if raw.startswith("<external>"):
        remainder = raw[len("<external>"):].lstrip("/")
        parts = _collapse_parts(remainder.split("/")) if remainder else tuple()
        return ParsedPath("external", "<external>", parts, False)

    if raw.startswith("//"):
        unc = raw.lstrip("/")
        segments = [seg for seg in unc.split("/") if seg]
        if len(segments) >= 2:
            root = f"{segments[0]}/{segments[1]}".lower()
            rest = segments[2:]
        elif segments:
            root = segments[0].lower()
            rest = []
        else:
            root = ""
            rest = []
        return ParsedPath("unc", root, _collapse_parts(rest), True)

    drive_match = _WINDOWS_DRIVE_RE.match(raw)
    if drive_match:
        drive = drive_match.group(1).lower()
        rest = drive_match.group(2).lstrip("/")
        parts = _collapse_parts(rest.split("/")) if rest else tuple()
        return ParsedPath("drive", drive, parts, True)

    wsl_match = _WSL_MNT_RE.match(raw)
    if wsl_match:
        drive = wsl_match.group(1).lower()
        rest = (wsl_match.group(2) or "").lstrip("/")
        parts = _collapse_parts(rest.split("/")) if rest else tuple()
        return ParsedPath("drive", drive, parts, True)

    wsl_drive = _WSL_DRIVE_RE.match(raw)
    if wsl_drive:
        drive = wsl_drive.group(1).lower()
        rest = (wsl_drive.group(2) or "").lstrip("/")
        parts = _collapse_parts(rest.split("/")) if rest else tuple()
        return ParsedPath("drive", drive, parts, True)

    if raw.startswith("/"):
        parts = _collapse_parts(raw.lstrip("/").split("/"))
        return ParsedPath("posix", "/", parts, False)

    parts = _collapse_parts(raw.split("/"))
    return ParsedPath("relative", "", parts, False)


def _parts_for_compare(parsed: ParsedPath) -> Tuple[str, ...]:
    if parsed.casefold:
        return tuple(part.lower() for part in parsed.parts)
    return parsed.parts


def is_absolute_path(path: str) -> bool:
    parsed = parse_path(path)
    return parsed.kind in ("posix", "drive", "unc")


def is_subpath(repo_root: str, path: str) -> bool:
    """Return True if path is equal to or under repo_root."""
    parsed_root = parse_path(repo_root)
    parsed_path = parse_path(path)

    if parsed_path.kind == "relative":
        return True
    if parsed_root.kind == "relative":
        return False
    if parsed_path.kind != parsed_root.kind or parsed_path.root != parsed_root.root:
        return False

    root_parts = _parts_for_compare(parsed_root)
    path_parts = _parts_for_compare(parsed_path)
    if len(path_parts) < len(root_parts):
        return False
    return path_parts[:len(root_parts)] == root_parts


def render_posix(parsed: ParsedPath) -> str:
    """Render a parsed path with POSIX separators."""
    if parsed.kind == "relative":
        return "/".join(parsed.parts) or "."
    if parsed.kind == "posix":
        return "/" + "/".join(parsed.parts) if parsed.parts else "/"
    if parsed.kind == "drive":
        suffix = "/".join(parsed.parts)
        if suffix:
            return f"{parsed.root.upper()}:/{suffix}"
        return f"{parsed.root.upper()}:/"
    if parsed.kind == "unc":
        suffix = "/".join(parsed.parts)
        if suffix:
            return f"//{parsed.root}/{suffix}"
        return f"//{parsed.root}"
    if parsed.kind == "external":
        suffix = "/".join(parsed.parts)
        return f"<external>/{suffix}" if suffix else "<external>"
    return "/".join(parsed.parts)


def normalize_path_to_posix(path: str) -> str:
    """Normalize a path to POSIX separators without changing relativeness."""
    parsed = parse_path(path)
    return render_posix(parsed)


def normalize_relpath(repo_root: str, path: str) -> str:
    """Return a repo-relative, POSIX path."""
    parsed_path = parse_path(path)
    if parsed_path.kind == "relative":
        return normalize_path_to_posix(path)

    parsed_root = parse_path(repo_root)
    if not is_subpath(repo_root, path):
        raise ValueError(f"Path is not under repo root: {path}")

    root_parts = parsed_root.parts
    rel_parts = parsed_path.parts[len(root_parts):] if root_parts else parsed_path.parts
    return "/".join(rel_parts) or "."


def externalize_path(path: str) -> str:
    """Wrap an external path with <external>/ prefix."""
    parsed = parse_path(path)
    rendered = render_posix(parsed)
    if rendered.startswith("<external>"):
        return rendered
    return f"<external>/{rendered.lstrip('/')}"


def normalize_repo_path(repo_root: str, path: str) -> Tuple[str, bool]:
    """
    Normalize a path for repo_model storage.

    Returns:
        (normalized_path, was_abs_under_root)
    """
    if path is None:
        return path, False
    if isinstance(path, Path):
        path = str(path)

    if str(path).startswith("<external>"):
        return normalize_path_to_posix(path), False

    if is_absolute_path(path):
        if is_subpath(repo_root, path):
            return normalize_relpath(repo_root, path), True
        real_root = os.path.realpath(repo_root)
        real_path = os.path.realpath(path)
        if (real_root != repo_root or real_path != path) and is_subpath(real_root, real_path):
            return normalize_relpath(real_root, real_path), True
        return externalize_path(path), False

    return normalize_path_to_posix(path), False


def expand_repo_path(repo_root: str, path: str) -> str:
    """Expand a repo-relative path to an absolute path for runtime use."""
    if path is None:
        return path
    if str(path).startswith("<external>"):
        return str(path)
    if is_absolute_path(str(path)):
        return str(path)
    return str(Path(repo_root) / Path(_normalize_slashes(str(path))))


def display_repo_path(repo_root: str, path: str) -> str:
    """Render a path for CLI display, preferring repo_root/relpath."""
    if path is None:
        return ""
    if str(path).startswith("<external>"):
        return str(path)
    if is_absolute_path(str(path)):
        return str(path)
    if not repo_root:
        return str(path)
    rel = normalize_path_to_posix(str(path))
    if rel in (".", ""):
        return str(repo_root)
    return str(Path(repo_root) / Path(rel))


def normalize_repo_model_paths(model: dict, repo_root: str) -> Tuple[dict, int]:
    """Normalize known repo_model path fields to repo-relative POSIX paths."""
    changed = 0

    def _normalize_list(paths: Iterable[str], relative_only: bool = False) -> list:
        normalized = []
        for item in paths:
            if relative_only:
                normalized.append(normalize_path_to_posix(item))
            else:
                value, was_abs = normalize_repo_path(repo_root, item)
                if was_abs:
                    nonlocal_changed[0] += 1
                normalized.append(value)
        return normalized

    nonlocal_changed = [0]

    for asm in model.get("assemblies_detected", []):
        root_path, was_abs = normalize_repo_path(repo_root, asm.get("root_path"))
        if was_abs:
            nonlocal_changed[0] += 1
        asm["root_path"] = root_path
        if asm.get("package_folders"):
            asm["package_folders"] = _normalize_list(asm.get("package_folders", []))
        if asm.get("package_dirs"):
            asm["package_dirs"] = _normalize_list(asm.get("package_dirs", []))

    for pkg in model.get("packages_detected", []):
        dir_path, was_abs = normalize_repo_path(repo_root, pkg.get("dir"))
        if was_abs:
            nonlocal_changed[0] += 1
        pkg["dir"] = dir_path

        upp_path = pkg.get("upp_path")
        if upp_path:
            normalized_upp, was_abs = normalize_repo_path(repo_root, upp_path)
            if was_abs:
                nonlocal_changed[0] += 1
            pkg["upp_path"] = normalized_upp

        if pkg.get("files"):
            pkg["files"] = _normalize_list(pkg.get("files", []), relative_only=True)

        for group in pkg.get("groups", []):
            if isinstance(group, dict) and group.get("files"):
                group["files"] = _normalize_list(group.get("files", []), relative_only=True)

        if pkg.get("ungrouped_files"):
            pkg["ungrouped_files"] = _normalize_list(pkg.get("ungrouped_files", []), relative_only=True)

        upp = pkg.get("upp")
        if isinstance(upp, dict) and upp.get("files"):
            for upp_file in upp.get("files", []):
                if isinstance(upp_file, dict) and upp_file.get("path"):
                    upp_file["path"] = normalize_path_to_posix(upp_file["path"])

    for unknown in model.get("unknown_paths", []):
        unknown_path, was_abs = normalize_repo_path(repo_root, unknown.get("path"))
        if was_abs:
            nonlocal_changed[0] += 1
        unknown["path"] = unknown_path

    for ipkg in model.get("internal_packages", []):
        root_path, was_abs = normalize_repo_path(repo_root, ipkg.get("root_path"))
        if was_abs:
            nonlocal_changed[0] += 1
        ipkg["root_path"] = root_path
        if ipkg.get("members"):
            ipkg["members"] = _normalize_list(ipkg.get("members", []), relative_only=True)
        if ipkg.get("groups"):
            for group in ipkg.get("groups", []):
                if isinstance(group, dict) and group.get("files"):
                    group["files"] = _normalize_list(group.get("files", []), relative_only=True)
        if ipkg.get("ungrouped_files"):
            ipkg["ungrouped_files"] = _normalize_list(ipkg.get("ungrouped_files", []), relative_only=True)

    for asm in model.get("assemblies", []):
        if "root_relpath" in asm:
            asm["root_relpath"] = normalize_path_to_posix(asm.get("root_relpath"))

    for pkg in model.get("packages", []):
        if "dir_relpath" in pkg:
            pkg["dir_relpath"] = normalize_path_to_posix(pkg.get("dir_relpath"))
        if "package_relpath" in pkg:
            pkg["package_relpath"] = normalize_path_to_posix(pkg.get("package_relpath"))

    for user in model.get("user_assemblies", []):
        for key in ("var_file",):
            if user.get(key):
                user[key] = normalize_repo_path(repo_root, user[key])[0]
        for key in ("upp_paths", "existing_paths", "repo_paths"):
            if user.get(key):
                user[key] = _normalize_list(user.get(key, []))

    changed = nonlocal_changed[0]
    return model, changed
