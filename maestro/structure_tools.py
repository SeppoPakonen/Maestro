from __future__ import annotations

import json
import os
import re
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from maestro.modules.dataclasses import (
    FixPlan,
    MatchCondition,
    RenameOperation,
    Rule,
    RuleAction,
    RuleMatch,
    RuleVerify,
    Rulebook,
    UppPackage,
    UppRepoIndex,
    WriteFileOperation,
)
from maestro.structure_fix import apply_fix_plan_operations

NOTE_COMMENT = "// NOTE: This header is normally included inside namespace Upp"


def get_fix_rulebooks_dir() -> str:
    base_dir = Path.home() / ".config" / "maestro" / "fix"
    (base_dir / "rulebooks").mkdir(parents=True, exist_ok=True)
    return str(base_dir)


def get_registry_file_path() -> str:
    base_dir = Path(get_fix_rulebooks_dir())
    return str(base_dir / "registry.json")


def load_registry() -> Dict[str, object]:
    registry_path = Path(get_registry_file_path())
    if not registry_path.exists():
        return {"repos": [], "active_rulebook": None}
    return json.loads(registry_path.read_text(encoding="utf-8"))


def save_rulebook(name: str, rulebook: Rulebook) -> str:
    rulebooks_dir = Path(get_fix_rulebooks_dir()) / "rulebooks"
    rulebooks_dir.mkdir(parents=True, exist_ok=True)
    path = rulebooks_dir / f"{name}.json"
    path.write_text(json.dumps(asdict(rulebook), indent=2), encoding="utf-8")
    return str(path)


def load_rulebook(name: str) -> Rulebook:
    rulebooks_dir = Path(get_fix_rulebooks_dir()) / "rulebooks"
    path = rulebooks_dir / f"{name}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    rules: List[Rule] = []
    for rule_data in data.get("rules", []):
        match_data = rule_data.get("match", {})
        match = RuleMatch(
            any=[MatchCondition(**cond) for cond in match_data.get("any", [])],
            not_conditions=[MatchCondition(**cond) for cond in match_data.get("not_conditions", [])],
        )
        actions = [RuleAction(**action) for action in rule_data.get("actions", [])]
        verify = RuleVerify(**rule_data.get("verify", {}))
        rules.append(
            Rule(
                id=rule_data.get("id", ""),
                enabled=rule_data.get("enabled", True),
                priority=rule_data.get("priority", 0),
                match=match,
                confidence=rule_data.get("confidence", 0.0),
                explanation=rule_data.get("explanation", ""),
                actions=actions,
                verify=verify,
            )
        )
    return Rulebook(
        version=data.get("version", 1),
        name=data.get("name", name),
        description=data.get("description", ""),
        rules=rules,
    )


def _guard_name(package_name: str, header_path: str) -> str:
    stem = Path(header_path).stem
    raw = f"{package_name}_{stem}_H"
    return re.sub(r"[^A-Za-z0-9]+", "_", raw).upper()


def fix_header_guards(header_path: str, package_name: str) -> bool:
    path = Path(header_path)
    if not path.exists():
        return False
    original = path.read_text(encoding="utf-8")
    guard = _guard_name(package_name, header_path)
    stripped_lines = []
    for line in original.splitlines():
        normalized = line.strip()
        if normalized.startswith("#pragma once"):
            continue
        if normalized.startswith("#ifndef") or normalized.startswith("#define"):
            continue
        if normalized.startswith("#endif"):
            continue
        stripped_lines.append(line)
    body = "\n".join(stripped_lines).strip()
    if body:
        body = f"{body}\n"
    content = (
        f"#ifndef {guard}\n"
        f"#define {guard}\n\n"
        f"{NOTE_COMMENT}\n\n"
        f"{body}\n"
        f"#endif // {guard}\n"
    )
    path.write_text(content, encoding="utf-8")
    return True


def ensure_main_header_content(package: UppPackage) -> List[WriteFileOperation]:
    if not package.main_header_path:
        return []
    guard = _guard_name(package.name, package.main_header_path)
    content = (
        f"#ifndef {guard}\n"
        f"#define {guard}\n\n"
        f"{NOTE_COMMENT}\n\n"
        f"// Main header for {package.name}\n\n"
        f"#endif // {guard}\n"
    )
    return [
        WriteFileOperation(
            op="write_file",
            reason="ensure_main_header_content",
            path=package.main_header_path,
            content=content,
        )
    ]


def normalize_cpp_includes(package: UppPackage) -> List[WriteFileOperation]:
    if not package.main_header_path:
        return []
    operations: List[WriteFileOperation] = []
    main_header = Path(package.main_header_path).name
    for source_path in package.source_files:
        source_file = Path(source_path)
        if not source_file.exists():
            continue
        content = source_file.read_text(encoding="utf-8")
        lines = content.splitlines()
        includes = [line for line in lines if line.strip().startswith("#include")]
        remaining = [line for line in lines if line.strip() and not line.strip().startswith("#include")]
        main_include = f'#include "{main_header}"'
        filtered_includes = [line for line in includes if main_header not in line]
        new_lines: List[str] = [main_include]
        new_lines.extend(filtered_includes)
        if remaining:
            new_lines.append("")
            new_lines.extend(remaining)
        new_content = "\n".join(new_lines).rstrip() + "\n"
        operations.append(
            WriteFileOperation(
                op="write_file",
                reason="normalize_cpp_includes",
                path=str(source_file),
                content=new_content,
            )
        )
    return operations


def reduce_secondary_header_includes(package: UppPackage) -> List[WriteFileOperation]:
    operations: List[WriteFileOperation] = []
    for header_path in package.header_files:
        if package.main_header_path and os.path.abspath(header_path) == os.path.abspath(package.main_header_path):
            continue
        header_file = Path(header_path)
        if not header_file.exists():
            continue
        content = header_file.read_text(encoding="utf-8")
        if NOTE_COMMENT in content:
            continue
        lines = content.splitlines()
        insert_at = 0
        for idx, line in enumerate(lines[:10]):
            if line.strip().startswith("#define"):
                insert_at = idx + 1
                break
        lines.insert(insert_at, "")
        lines.insert(insert_at + 1, NOTE_COMMENT)
        new_content = "\n".join(lines).rstrip() + "\n"
        operations.append(
            WriteFileOperation(
                op="write_file",
                reason="reduce_secondary_header_includes",
                path=str(header_file),
                content=new_content,
            )
        )
    return operations


def _parse_upp_uses(upp_path: str) -> List[str]:
    path = Path(upp_path)
    if not path.exists():
        return []
    uses: List[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip().startswith("uses"):
            uses.extend(re.findall(r'"([^"]+)"', line))
    return uses


def scan_upp_repo(repo_root: str, verbose: bool = False, assemblies: Optional[List[str]] = None) -> UppRepoIndex:
    if assemblies is None:
        assemblies = [repo_root]
    assembly_paths = [str(Path(path)) for path in assemblies]
    if verbose:
        print(f"[maestro] assemblies: {assembly_paths}")
    packages: List[UppPackage] = []
    for assembly in assembly_paths:
        assembly_path = Path(assembly)
        if verbose:
            print(f"scanning assembly: {assembly}")
        if not assembly_path.exists():
            continue
        upp_files = sorted(
            upp for upp in assembly_path.rglob("*.upp") if ".maestro" not in upp.parts
        )
        package_dirs = sorted({upp.parent for upp in upp_files})
        if verbose:
            print(f"package folders: {len(package_dirs)}")
        for pkg_dir in package_dirs:
            primary_upp = pkg_dir / f"{pkg_dir.name}.upp"
            if primary_upp.exists():
                upp_file = primary_upp
            else:
                upp_file = next((upp for upp in upp_files if upp.parent == pkg_dir), None)
                if upp_file is None:
                    continue
            pkg_name = upp_file.stem
            main_header = pkg_dir / f"{pkg_name}.h"
            source_files = sorted(str(path) for path in pkg_dir.glob("*.cpp"))
            header_files = sorted(str(path) for path in pkg_dir.glob("*.h"))
            packages.append(
                UppPackage(
                    name=pkg_name,
                    dir_path=str(pkg_dir),
                    upp_path=str(upp_file),
                    main_header_path=str(main_header) if main_header.exists() else None,
                    source_files=source_files,
                    header_files=header_files,
                )
            )
            if verbose:
                print(f"FOUND (package: {pkg_name}) -> {pkg_dir}")
    return UppRepoIndex(assemblies=assembly_paths, packages=packages)


def resolve_upp_dependencies(
    repo_index: UppRepoIndex, package_name: str, verbose: bool = False
) -> Dict[str, Optional[UppPackage]]:
    package = next((pkg for pkg in repo_index.packages if pkg.name == package_name), None)
    if not package:
        return {}
    dependencies = _parse_upp_uses(package.upp_path)
    resolved: Dict[str, Optional[UppPackage]] = {}
    for dependency in dependencies:
        match = next((pkg for pkg in repo_index.packages if pkg.name == dependency), None)
        resolved[dependency] = match
        if verbose:
            location = match.dir_path if match else "NOT FOUND"
            print(f"resolve dependency: {dependency} -> {location}")
    return resolved


def _structure_dir(repo_root: str) -> Path:
    return Path(repo_root) / ".maestro" / "build" / "structure"


def _capital_case(name: str) -> str:
    return name[:1].upper() + name[1:] if name else name


def _scan_structure_repo(repo_root: str) -> Dict[str, object]:
    root_path = Path(repo_root)
    packages: List[Dict[str, str]] = []
    casing_issues: List[Dict[str, str]] = []
    missing_upp: List[Dict[str, str]] = []

    upp_files = [
        upp for upp in root_path.rglob("*.upp") if ".maestro" not in upp.parts
    ]
    for upp_file in upp_files:
        pkg_dir = upp_file.parent
        pkg_name = upp_file.stem
        packages.append(
            {"name": pkg_name, "dir": str(pkg_dir), "upp_path": str(upp_file)}
        )
        expected = _capital_case(pkg_name)
        if pkg_name != expected:
            casing_issues.append(
                {
                    "name": pkg_name,
                    "dir": str(pkg_dir),
                    "expected_name": expected,
                }
            )

    for directory in root_path.rglob("*"):
        if ".maestro" in directory.parts or not directory.is_dir():
            continue
        entries = list(directory.iterdir())
        has_sources = any(entry.suffix in (".cpp", ".h") for entry in entries if entry.is_file())
        has_upp = any(entry.suffix == ".upp" for entry in entries if entry.is_file())
        if has_sources and not has_upp:
            missing_upp.append(
                {
                    "dir": str(directory),
                    "expected_upp": str(directory / f"{directory.name}.upp"),
                }
            )

    summary = {
        "packages_found": len(packages),
        "casing_issues_count": len(casing_issues),
        "missing_upp_count": len(missing_upp),
    }
    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "summary": summary,
        "packages": packages,
        "casing_issues": casing_issues,
        "missing_upp": missing_upp,
    }


def _fix_plan_to_dict(plan: FixPlan) -> Dict[str, object]:
    ops = []
    for op in plan.operations:
        if isinstance(op, RenameOperation):
            ops.append(
                {
                    "op": op.op,
                    "reason": op.reason,
                    "from": op.from_path,
                    "to": op.to_path,
                }
            )
        elif isinstance(op, WriteFileOperation):
            ops.append(
                {
                    "op": op.op,
                    "reason": op.reason,
                    "path": op.path,
                    "content": op.content,
                }
            )
        else:
            ops.append(asdict(op))
    return {
        "version": plan.version,
        "repo_root": plan.repo_root,
        "generated_at": plan.generated_at,
        "operations": ops,
    }


def _load_fix_plan(path: Path) -> FixPlan:
    data = json.loads(path.read_text(encoding="utf-8"))
    operations = []
    for op in data.get("operations", []):
        op_type = op.get("op")
        if op_type == "rename":
            operations.append(
                RenameOperation(
                    op="rename",
                    reason=op.get("reason", ""),
                    from_path=op.get("from") or op.get("from_path", ""),
                    to_path=op.get("to") or op.get("to_path", ""),
                )
            )
        elif op_type == "write_file":
            operations.append(
                WriteFileOperation(
                    op="write_file",
                    reason=op.get("reason", ""),
                    path=op.get("path", ""),
                    content=op.get("content", ""),
                )
            )
    return FixPlan(
        version=data.get("version", 1),
        repo_root=data.get("repo_root", ""),
        generated_at=data.get("generated_at", ""),
        operations=operations,
    )


def _build_fix_plan(
    scan_report: Dict[str, object],
    repo_root: str,
    only_rules: Optional[List[str]] = None,
    skip_rules: Optional[List[str]] = None,
) -> FixPlan:
    active_rules = ["capital_case_names", "ensure_upp_exists"]
    if only_rules:
        active_rules = only_rules
    if skip_rules:
        active_rules = [rule for rule in active_rules if rule not in skip_rules]

    operations: List[object] = []
    if "capital_case_names" in active_rules:
        for issue in scan_report.get("casing_issues", []):
            pkg_dir = Path(issue["dir"])
            old_name = issue["name"]
            new_name = issue["expected_name"]
            old_upp = pkg_dir / f"{old_name}.upp"
            new_upp = pkg_dir / f"{new_name}.upp"
            if old_upp.exists():
                operations.append(
                    RenameOperation(
                        op="rename",
                        reason="capital_case_names",
                        from_path=str(old_upp),
                        to_path=str(new_upp),
                    )
                )
            operations.append(
                RenameOperation(
                    op="rename",
                    reason="capital_case_names",
                    from_path=str(pkg_dir),
                    to_path=str(pkg_dir.parent / new_name),
                )
            )

    if "ensure_upp_exists" in active_rules:
        for missing in scan_report.get("missing_upp", []):
            missing_dir = Path(missing["dir"])
            target_upp = missing_dir / f"{missing_dir.name}.upp"
            operations.append(
                WriteFileOperation(
                    op="write_file",
                    reason="ensure_upp_exists",
                    path=str(target_upp),
                    content=f"uses ;\nfile \"{missing_dir.name}.cpp\";\n",
                )
            )

    return FixPlan(repo_root=repo_root, operations=operations)


def handle_structure_scan(session_path: str, verbose: bool = False, target: Optional[str] = None):
    repo_root = target or os.getcwd()
    structure_dir = _structure_dir(repo_root)
    structure_dir.mkdir(parents=True, exist_ok=True)
    report = _scan_structure_repo(repo_root)
    scan_path = structure_dir / "last_scan.json"
    scan_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if verbose:
        print(f"Using structure directory: {structure_dir}")
        print(f"Scan file: {scan_path}")
    return report


def handle_structure_show(session_path: str, verbose: bool = False, target: Optional[str] = None):
    repo_root = target or os.getcwd()
    structure_dir = _structure_dir(repo_root)
    scan_path = structure_dir / "last_scan.json"
    if not scan_path.exists():
        report = handle_structure_scan(session_path, verbose=verbose, target=repo_root)
    else:
        report = json.loads(scan_path.read_text(encoding="utf-8"))
    summary = report.get("summary", {})
    print(f"Packages found: {summary.get('packages_found', 0)}")
    print(f"Casing issues: {summary.get('casing_issues_count', 0)}")
    print(f"Missing .upp files: {summary.get('missing_upp_count', 0)}")
    print("TOP 10 OFFENDERS")
    for issue in report.get("casing_issues", [])[:10]:
        print(f"- {issue.get('name')} -> {issue.get('expected_name')}")
    return report


def handle_structure_fix(
    session_path: str,
    verbose: bool = False,
    apply_directly: bool = False,
    dry_run: bool = False,
    limit: Optional[int] = None,
    target: Optional[str] = None,
    only_rules: Optional[str] = None,
    skip_rules: Optional[str] = None,
):
    repo_root = target or os.getcwd()
    structure_dir = _structure_dir(repo_root)
    structure_dir.mkdir(parents=True, exist_ok=True)
    scan_path = structure_dir / "last_scan.json"
    if not scan_path.exists():
        report = handle_structure_scan(session_path, verbose=verbose, target=repo_root)
    else:
        report = json.loads(scan_path.read_text(encoding="utf-8"))

    rules = [rule.strip() for rule in (only_rules or "").split(",") if rule.strip()]
    skip = [rule.strip() for rule in (skip_rules or "").split(",") if rule.strip()]
    only_rules_list = rules or None
    skip_rules_list = skip or None
    fix_plan = _build_fix_plan(report, repo_root, only_rules_list, skip_rules_list)
    if limit is not None:
        fix_plan.operations = fix_plan.operations[:limit]

    plan_path = structure_dir / "last_fix_plan.json"
    plan_path.write_text(json.dumps(_fix_plan_to_dict(fix_plan), indent=2), encoding="utf-8")

    print(f"Fix plan generated with {len(fix_plan.operations)} operations")
    print(f"Total operations: {len(fix_plan.operations)}")
    print(f"Rules to run: {', '.join(only_rules_list or ['capital_case_names', 'ensure_upp_exists'])}")
    if fix_plan.operations:
        print("First 10 operations:")
        for op in fix_plan.operations[:10]:
            print(f"- {op.op}: {getattr(op, 'reason', '')}")

    if verbose:
        print(f"Using structure directory: {structure_dir}")
        print(f"Scan file: {scan_path}")
        print(f"Fix plan file: {plan_path}")

    if apply_directly and not dry_run:
        apply_fix_plan_operations(fix_plan, verbose=verbose)
    return fix_plan


def handle_structure_apply(
    session_path: str,
    verbose: bool = False,
    limit: Optional[int] = None,
    target: Optional[str] = None,
    dry_run: bool = False,
):
    repo_root = target or os.getcwd()
    structure_dir = _structure_dir(repo_root)
    plan_path = structure_dir / "last_fix_plan.json"
    if not plan_path.exists():
        return 1
    fix_plan = _load_fix_plan(plan_path)
    if limit is not None:
        fix_plan.operations = fix_plan.operations[:limit]
    if dry_run:
        return 0
    apply_fix_plan_operations(fix_plan, verbose=verbose)
    return 0


def handle_structure_lint(session_path: str, verbose: bool = False, target: Optional[str] = None):
    handle_structure_scan(session_path, verbose=verbose, target=target)
    return 0


def apply_structure_fix_rules(
    repo_root: str, apply_rules: List[str], limit: Optional[int] = None, verbose: bool = False
) -> FixPlan:
    report = _scan_structure_repo(repo_root)
    plan = _build_fix_plan(report, repo_root, only_rules=apply_rules, skip_rules=None)
    if limit is not None:
        plan.operations = plan.operations[:limit]
    if verbose:
        print(f"Structure fix rules applied: {apply_rules}")
    return plan


def execute_structure_fix_action(
    repo_root: str, action: RuleAction, verbose: bool = False
) -> Optional[FixPlan]:
    if action.type != "structure_fix":
        return None
    return apply_structure_fix_rules(
        repo_root,
        apply_rules=action.apply_rules,
        limit=action.limit,
        verbose=verbose,
    )


def run_structure_fixes_from_rulebooks(repo_root: str, verbose: bool = False) -> List[FixPlan]:
    registry = load_registry()
    abs_root = os.path.abspath(repo_root)
    rulebook_name = None
    for repo_entry in registry.get("repos", []):
        if repo_entry.get("abs_path") == abs_root:
            rulebook_name = repo_entry.get("rulebook")
            break
    if not rulebook_name:
        return []
    rulebook = load_rulebook(rulebook_name)
    plans: List[FixPlan] = []
    for rule in rulebook.rules:
        for action in rule.actions:
            plan = execute_structure_fix_action(repo_root, action, verbose=verbose)
            if plan:
                plans.append(plan)
    return plans
