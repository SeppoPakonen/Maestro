"""
Tutorial command implementation for Maestro CLI.

Commands:
- maestro tutorial - Show tutorial instructions for basic project management
"""

def add_tutorial_parser(subparsers):
    """
    Add tutorial command parser to the main argument parser.
    """
    tutorial_parser = subparsers.add_parser(
        'tutorial',
        aliases=['tut'],
        help='Show tutorial for basic project management'
    )
    tutorial_parser.set_defaults(func=handle_tutorial_command)


def handle_tutorial_command(args):
    """
    Handle the tutorial command.
    """
    print_tutorial()


def print_tutorial():
    """
    Print the tutorial content.
    """
    tutorial_text = """
MAESTRO TUTORIAL

Welcome to Maestro! Here's how to get started with basic project management:

1. PROJECT SETUP
   - Initialize a new project: maestro init
   - For new repositories, run: maestro repo resolve

2. BASIC PROJECT MANAGEMENT
   - Track your work with tracks, phases, and tasks
   - View available commands:
     * maestro track --help    # For managing project tracks
     * maestro phase --help    # For managing project phases  
     * maestro task --help     # For managing individual tasks

3. COMMON WORKFLOW
   - Create a track: maestro track add "My Track Name"
   - Add phases to your track: maestro phase add --track <track_id> "Phase Name"
   - Add tasks to phases: maestro task add --phase <phase_id> "Task Name"
   - List your work: maestro task list
   - Update task status: maestro task <task_id> complete

4. NEXT STEPS
   - Explore repository structure: maestro repo hier
   - Discuss work with AI: maestro track <id> discuss

For detailed help on any command, use --help:
   maestro track --help
   maestro phase --help
   maestro task --help
"""
    print(tutorial_text)