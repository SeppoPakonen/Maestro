"""
Parser for the understand dump command.
"""
import argparse


def add_understand_parser(subparsers):
    """
    Add understand command parser to the main argument parser.
    """
    understand_parser = subparsers.add_parser(
        'understand',
        aliases=['u'],
        help='[DEPRECATED] Use repo resolve or runbook instead',
        description='[DEPRECATED] Use repo resolve or runbook instead'
    )
    
    understand_subparsers = understand_parser.add_subparsers(
        dest='understand_subcommand',
        help='Understand subcommands'
    )
    
    # Add the dump subcommand
    dump_parser = understand_subparsers.add_parser(
        'dump',
        aliases=['d'],
        help='Generate project understanding snapshot as Markdown'
    )
    dump_parser.add_argument(
        '--output', '-o',
        dest='output_path',
        help='Output file path (default: docs/UNDERSTANDING_SNAPSHOT.md)'
    )
    dump_parser.add_argument(
        '--check',
        action='store_true',
        help='Exit non-zero if snapshot would change (useful in CI)'
    )
    
    return understand_parser
