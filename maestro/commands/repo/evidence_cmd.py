"""
Repository evidence pack commands (pack, list, show).

Handles deterministic evidence collection for AI workflows.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from maestro.modules.utils import (
    print_header,
    print_warning,
    print_error,
    print_info,
)


def handle_repo_evidence_pack(args, repo_root: Path):
    """
    Generate evidence pack from repository.

    Args:
        args: Parsed command-line arguments
        repo_root: Path to repository root
    """
    from maestro.repo.profile import load_profile
    from maestro.repo.evidence_pack import (
        EvidenceCollector,
        save_evidence_pack
    )

    # Load profile if it exists
    profile = load_profile(repo_root)

    # Get budgets (CLI args override profile override defaults)
    if profile and profile.evidence_rules:
        max_files = args.max_files or profile.evidence_rules.max_files
        max_bytes = args.max_bytes or profile.evidence_rules.max_bytes
        max_help_calls = args.max_help_calls or profile.evidence_rules.max_help_calls
        timeout_seconds = profile.evidence_rules.timeout_seconds
        prefer_dirs = profile.evidence_rules.prefer_dirs
        exclude_patterns = profile.evidence_rules.exclude_patterns
    else:
        max_files = args.max_files or 60
        max_bytes = args.max_bytes or 250000
        max_help_calls = args.max_help_calls or 6
        timeout_seconds = 5
        prefer_dirs = []
        exclude_patterns = []

    if args.verbose:
        print_info("Collecting evidence...", 2)
        print(f"  Max files:       {max_files}")
        print(f"  Max bytes:       {max_bytes}")
        print(f"  Max help calls:  {max_help_calls}")

    # Create collector
    collector = EvidenceCollector(
        repo_root=repo_root,
        max_files=max_files,
        max_bytes=max_bytes,
        max_help_calls=max_help_calls,
        timeout_seconds=timeout_seconds,
        prefer_dirs=prefer_dirs,
        exclude_patterns=exclude_patterns
    )

    # Get CLI candidates from profile
    cli_candidates = None
    if profile:
        cli_candidates = profile.cli_help_candidates

    # Collect evidence
    pack = collector.collect_all(cli_candidates=cli_candidates)

    # Output or save
    if args.json:
        # Output to stdout
        print(json.dumps(pack.to_dict(), indent=2))
    else:
        # Human-readable summary
        print_header("EVIDENCE PACK")
        print(f"\nPack ID:         {pack.meta.pack_id}")
        print(f"Evidence count:  {pack.meta.evidence_count}")
        print(f"Total bytes:     {pack.meta.total_bytes:,}")
        print(f"\nFiles processed: {pack.meta.budget_applied['files_processed']}/{max_files}")
        print(f"Help calls made: {pack.meta.budget_applied['help_calls_made']}/{max_help_calls}")

        if pack.meta.truncated_items:
            print(f"\nTruncated items: {len(pack.meta.truncated_items)}")
            if args.verbose:
                for item in pack.meta.truncated_items[:5]:
                    print(f"  - {item}")
                if len(pack.meta.truncated_items) > 5:
                    print(f"  ... and {len(pack.meta.truncated_items) - 5} more")

        if pack.meta.skipped_items:
            print(f"\nSkipped items (budget): {len(pack.meta.skipped_items)}")
            if args.verbose:
                for item in pack.meta.skipped_items[:5]:
                    print(f"  - {item}")
                if len(pack.meta.skipped_items) > 5:
                    print(f"  ... and {len(pack.meta.skipped_items) - 5} more")

        # Save if requested
        if args.save:
            storage_dir = repo_root / "docs" / "maestro" / "evidence_packs"
            pack_dir = save_evidence_pack(pack, storage_dir)
            print(f"\nSaved to: {pack_dir}")
        else:
            print("\nUse --save to store this pack for reuse")


def handle_repo_evidence_list(args, repo_root: Path):
    """
    List saved evidence packs.

    Args:
        args: Parsed command-line arguments
        repo_root: Path to repository root
    """
    from maestro.repo.evidence_pack import find_evidence_packs

    storage_dir = repo_root / "docs" / "maestro" / "evidence_packs"

    pack_ids = find_evidence_packs(storage_dir)

    if args.json:
        output = {
            "storage_dir": str(storage_dir),
            "packs": pack_ids
        }
        print(json.dumps(output, indent=2))
    else:
        if not pack_ids:
            print_warning(f"No evidence packs found in {storage_dir}", 2)
            print_info("Run 'maestro repo evidence pack --save' to create one", 2)
        else:
            print_header("EVIDENCE PACKS")
            print(f"\nStorage dir: {storage_dir}\n")
            for pack_id in pack_ids:
                print(f"  - {pack_id}")
            print(f"\nTotal: {len(pack_ids)} packs")


def handle_repo_evidence_show(args, repo_root: Path):
    """
    Show evidence pack details.

    Args:
        args: Parsed command-line arguments
        repo_root: Path to repository root
    """
    from maestro.repo.evidence_pack import load_evidence_pack

    storage_dir = repo_root / "docs" / "maestro" / "evidence_packs"

    pack = load_evidence_pack(args.pack_id, storage_dir)

    if not pack:
        print_error(f"Evidence pack not found: {args.pack_id}", 2)
        print_info(f"Storage dir: {storage_dir}", 2)
        sys.exit(1)

    if args.json:
        # Full JSON output
        print(json.dumps(pack.to_dict(), indent=2))
    else:
        # Human-readable summary
        print_header(f"EVIDENCE PACK: {args.pack_id}")
        print(f"\nCreated:         {pack.meta.created_at}")
        print(f"Repo root:       {pack.meta.repo_root}")
        print(f"Evidence count:  {pack.meta.evidence_count}")
        print(f"Total bytes:     {pack.meta.total_bytes:,}")

        print("\nBudget applied:")
        for key, value in pack.meta.budget_applied.items():
            print(f"  {key}: {value}")

        if pack.meta.truncated_items:
            print(f"\nTruncated: {len(pack.meta.truncated_items)} items")

        if pack.meta.skipped_items:
            print(f"Skipped:   {len(pack.meta.skipped_items)} items")

        print("\nEvidence items:")
        kind_counts = {}
        for item in pack.items:
            kind_counts[item.kind] = kind_counts.get(item.kind, 0) + 1

        for kind, count in sorted(kind_counts.items()):
            print(f"  {kind}: {count}")

        if args.show_content:
            print("\nItem details:")
            for i, item in enumerate(pack.items, 1):
                print(f"\n--- Item {i}: {item.source} ({item.kind}) ---")
                print(f"Size: {item.size_bytes} bytes")
                if item.truncated:
                    print("(truncated)")
                print(item.content[:500])  # First 500 chars
                if len(item.content) > 500:
                    print(f"\n... ({len(item.content) - 500} more chars)")
