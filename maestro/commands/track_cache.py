"""CLI for managing the persistent track data cache."""

from pathlib import Path

from maestro.data.track_cache import TrackDataCache


def add_track_cache_parser(subparsers):
    """Add the 'track-cache' CLI parser."""
    parser = subparsers.add_parser(
        "track-cache",
        help="Manage the persistent track/phase/task cache (located in ~/.maestro/track_cache).",
    )
    cache_subparsers = parser.add_subparsers(dest="track_cache_subcommand")

    invalidate_parser = cache_subparsers.add_parser(
        "invalidate",
        help="Invalidate the cached track data for the current repo.",
    )
    invalidate_parser.add_argument(
        "--repo",
        "-r",
        default=".",
        help="Repo root path (default: current working directory)",
    )


def handle_track_cache_command(args):
    """Dispatch track-cache subcommands."""
    if args.track_cache_subcommand == "invalidate":
        return handle_invalidate(args)

    print("Error: No track-cache subcommand specified")
    print("Available subcommands: invalidate")
    return 1


def handle_invalidate(args):
    """Handle the track-cache invalidate subcommand."""
    repo_root = Path(args.repo).resolve()
    cache = TrackDataCache(repo_root)
    if cache.invalidate():
        print(f"Invalidated track data cache for {repo_root}")
    else:
        print(f"No cached track data found for {repo_root}")
    return 0
