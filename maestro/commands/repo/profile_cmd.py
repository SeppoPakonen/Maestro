"""
Repository profile commands (init, show).

Handles profile management for repository-specific evidence collection settings.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from maestro.modules.utils import (
    print_header,
    print_success,
    print_warning,
    print_error,
    print_info,
)


def handle_repo_profile_show(args, repo_root: Path):
    """
    Show repository profile.

    Args:
        args: Parsed command-line arguments
        repo_root: Path to repository root
    """
    from maestro.repo.profile import load_profile, find_profile_path, infer_profile_from_repo

    # Try to load existing profile
    profile = load_profile(repo_root)
    profile_path = find_profile_path(repo_root)

    if args.json:
        if profile:
            print(json.dumps(profile.to_dict(), indent=2))
        else:
            # Return inferred profile in JSON mode
            inferred = infer_profile_from_repo(repo_root)
            output = {
                "status": "inferred",
                "note": "No profile found, showing inferred values",
                "profile": inferred.to_dict()
            }
            print(json.dumps(output, indent=2))
    else:
        if profile:
            print_header("REPOSITORY PROFILE")
            print(f"\nProfile path: {profile_path}\n")
            print(f"Product name:      {profile.product_name or '(not set)'}")
            print(f"Primary language:  {profile.primary_language or '(not set)'}")

            if profile.build_entrypoints:
                print(f"\nBuild entrypoints:")
                for entry in profile.build_entrypoints:
                    print(f"  - {entry}")

            if profile.docs_hints:
                print(f"\nDocs hints:")
                for hint in profile.docs_hints:
                    print(f"  - {hint}")

            if profile.cli_help_candidates:
                print(f"\nCLI help candidates:")
                for candidate in profile.cli_help_candidates:
                    print(f"  - {candidate}")

            print(f"\nEvidence rules:")
            print(f"  max_files:       {profile.evidence_rules.max_files}")
            print(f"  max_bytes:       {profile.evidence_rules.max_bytes}")
            print(f"  max_help_calls:  {profile.evidence_rules.max_help_calls}")
            print(f"  timeout_seconds: {profile.evidence_rules.timeout_seconds}")

            if profile.evidence_rules.prefer_dirs:
                print(f"  prefer_dirs:     {', '.join(profile.evidence_rules.prefer_dirs)}")
            if profile.evidence_rules.exclude_patterns:
                print(f"  exclude_patterns: {', '.join(profile.evidence_rules.exclude_patterns)}")
        else:
            print_warning(f"No profile found in {repo_root}", 2)
            print_info("Run 'maestro repo profile init' to create one", 2)
            print("")
            print_info("Inferred profile (not saved):", 2)
            inferred = infer_profile_from_repo(repo_root)
            print(f"  Product name:      {inferred.product_name}")
            print(f"  Primary language:  {inferred.primary_language or '(auto-detect)'}")
            if inferred.build_entrypoints:
                print(f"  Build entrypoints: {', '.join(inferred.build_entrypoints)}")


def handle_repo_profile_init(args, repo_root: Path):
    """
    Initialize repository profile with heuristic inference.

    Args:
        args: Parsed command-line arguments
        repo_root: Path to repository root
    """
    from maestro.repo.profile import (
        load_profile,
        infer_profile_from_repo,
        save_profile,
        find_profile_path
    )

    # Check if profile already exists
    existing_path = find_profile_path(repo_root)
    if existing_path and not args.force:
        print_error(f"Profile already exists at: {existing_path}", 2)
        print_info("Use --force to overwrite", 2)
        sys.exit(1)

    # Infer profile from repo
    print_info("Inferring profile from repository structure...", 2)
    profile = infer_profile_from_repo(repo_root)

    # Determine save location
    prefer_maestro_dir = not args.dot_maestro  # Default to docs/maestro/

    # Save profile
    saved_path = save_profile(profile, repo_root, prefer_maestro_dir=prefer_maestro_dir)

    print_success(f"Profile created: {saved_path}", 2)
    print("")
    print_info("Profile summary:", 2)
    print(f"  Product name:      {profile.product_name}")
    print(f"  Primary language:  {profile.primary_language or '(auto-detected)'}")

    if profile.build_entrypoints:
        print(f"  Build entrypoints: {len(profile.build_entrypoints)}")
        for entry in profile.build_entrypoints[:3]:
            print(f"    - {entry}")
        if len(profile.build_entrypoints) > 3:
            print(f"    ... and {len(profile.build_entrypoints) - 3} more")

    if profile.docs_hints:
        print(f"  Docs hints:        {len(profile.docs_hints)}")

    if profile.cli_help_candidates:
        print(f"  CLI candidates:    {len(profile.cli_help_candidates)}")

    print("")
    print_info("Edit the profile file to customize values", 2)
