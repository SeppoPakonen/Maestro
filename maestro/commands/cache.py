"""Cache management commands for Maestro."""

from maestro.ai.cache import AiCacheStore


def handle_cache_stats(args) -> int:
    """Show cache statistics.

    Args:
        args: Command arguments

    Returns:
        Exit code (0 for success)
    """
    cache_store = AiCacheStore()

    # Get stats for both scopes
    user_entries = cache_store.list_entries("user")
    repo_entries = cache_store.list_entries("repo")

    # Count by engine
    user_by_engine = {}
    repo_by_engine = {}

    for entry in user_entries:
        engine = entry.get("engine_kind", "unknown")
        user_by_engine[engine] = user_by_engine.get(engine, 0) + 1

    for entry in repo_entries:
        engine = entry.get("engine_kind", "unknown")
        repo_by_engine[engine] = repo_by_engine.get(engine, 0) + 1

    # Print stats
    print("AI Cache Statistics")
    print("=" * 60)
    print()

    print(f"User Cache ({cache_store.user_cache_root}):")
    print(f"  Total entries: {len(user_entries)}")
    if user_by_engine:
        print("  By engine:")
        for engine, count in sorted(user_by_engine.items()):
            print(f"    {engine}: {count}")
    print()

    print(f"Repo Cache ({cache_store.repo_cache_root}):")
    if cache_store.repo_cache_root.exists():
        print(f"  Total entries: {len(repo_entries)}")
        if repo_by_engine:
            print("  By engine:")
            for engine, count in sorted(repo_by_engine.items()):
                print(f"    {engine}: {count}")
    else:
        print("  Not initialized (no repo cache)")
    print()

    # Show configuration
    print("Configuration:")
    print(f"  Cache enabled: {cache_store.get_cache_enabled()}")
    print(f"  Cache scope: {cache_store.get_cache_scope()}")
    watch_patterns = cache_store.get_watch_patterns()
    if watch_patterns:
        print(f"  Watch patterns: {', '.join(watch_patterns)}")
    else:
        print("  Watch patterns: None (minimal fingerprinting)")
    print()

    return 0


def handle_cache_show(args) -> int:
    """Show details of a specific cache entry.

    Args:
        args: Command arguments with prompt_hash

    Returns:
        Exit code (0 for success, 1 for not found)
    """
    cache_store = AiCacheStore()
    prompt_hash = args.prompt_hash

    # Lookup entry
    result = cache_store.lookup(prompt_hash)
    if not result:
        print(f"Error: Cache entry not found: {prompt_hash}")
        return 1

    scope, entry_dir = result
    entry_data = cache_store.load_entry(entry_dir)

    # Print entry details
    print(f"Cache Entry: {prompt_hash}")
    print("=" * 60)
    print()

    # Meta
    if "meta" in entry_data:
        meta = entry_data["meta"]
        print("Metadata:")
        print(f"  Scope: {scope}")
        print(f"  Engine: {meta.get('engine_kind')}")
        print(f"  Model: {meta.get('model')}")
        print(f"  Created: {meta.get('created_at')}")
        print(f"  Validity: {meta.get('validity')}")
        print(f"  Apply mode: {meta.get('apply_mode')}")
        if meta.get('context_kind'):
            print(f"  Context: {meta.get('context_kind')}")
            if meta.get('context_ref'):
                print(f"  Context ref: {meta.get('context_ref')}")
        if meta.get('notes'):
            print(f"  Notes: {meta.get('notes')}")
        print()

    # Prompt
    if "prompt" in entry_data:
        prompt = entry_data["prompt"]
        print("Prompt:")
        print(f"  {prompt[:200]}{'...' if len(prompt) > 200 else ''}")
        print()

    # Ops
    if "ops" in entry_data:
        ops = entry_data["ops"]
        print(f"Operations ({len(ops)}):")
        for i, op in enumerate(ops, 1):
            print(f"  {i}. {op.get('op_type')}: {op.get('data')}")
        print()

    # Workspace
    if "workspace" in entry_data:
        workspace = entry_data["workspace"]
        print("Workspace Fingerprint:")
        if workspace.git_head:
            print(f"  Git HEAD: {workspace.git_head[:12]}...")
        print(f"  Git dirty: {workspace.git_dirty}")
        if workspace.watched_files:
            print(f"  Watched files: {len(workspace.watched_files)}")
            for file_path, file_hash in list(workspace.watched_files.items())[:5]:
                print(f"    {file_path}: {file_hash[:12]}...")
            if len(workspace.watched_files) > 5:
                print(f"    ... and {len(workspace.watched_files) - 5} more")
        print()

    # Patch
    if "patch" in entry_data:
        patch = entry_data["patch"]
        print(f"Patch diff:")
        print(f"  {len(patch)} bytes")
        print()

    return 0


def handle_cache_prune(args) -> int:
    """Prune old cache entries.

    Args:
        args: Command arguments with scope and older_than

    Returns:
        Exit code (0 for success)
    """
    cache_store = AiCacheStore()

    scope = getattr(args, 'scope', 'user')
    older_than = getattr(args, 'older_than', 30)

    print(f"Pruning {scope} cache entries older than {older_than} days...")

    deleted_count = cache_store.prune_old_entries(scope, older_than_days=older_than)

    print(f"Deleted {deleted_count} entries.")

    return 0


def handle_cache_command(args) -> int:
    """Handle cache subcommands.

    Args:
        args: Command arguments

    Returns:
        Exit code
    """
    cache_subcommand = getattr(args, "cache_subcommand", None)

    if cache_subcommand == "stats":
        return handle_cache_stats(args)
    elif cache_subcommand == "show":
        return handle_cache_show(args)
    elif cache_subcommand == "prune":
        return handle_cache_prune(args)
    else:
        print("Error: No cache subcommand specified")
        print("Available subcommands: stats, show, prune")
        return 1


def add_cache_parser(subparsers):
    """Add cache command parser.

    Args:
        subparsers: Subparsers from main argument parser
    """
    cache_parser = subparsers.add_parser(
        "cache",
        help="Manage AI cache"
    )

    cache_subparsers = cache_parser.add_subparsers(
        dest="cache_subcommand",
        help="Cache subcommands"
    )

    # Stats subcommand
    stats_parser = cache_subparsers.add_parser(
        "stats",
        help="Show cache statistics"
    )

    # Show subcommand
    show_parser = cache_subparsers.add_parser(
        "show",
        help="Show cache entry details"
    )
    show_parser.add_argument(
        "prompt_hash",
        help="Prompt hash (or prefix) of cache entry to show"
    )

    # Prune subcommand
    prune_parser = cache_subparsers.add_parser(
        "prune",
        help="Prune old cache entries"
    )
    prune_parser.add_argument(
        "--scope",
        choices=["user", "repo"],
        default="user",
        help="Cache scope to prune (default: user)"
    )
    prune_parser.add_argument(
        "--older-than",
        type=int,
        default=30,
        help="Delete entries older than N days (default: 30)"
    )

    return cache_parser
