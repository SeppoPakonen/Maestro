"""
Tutorial command implementation for Maestro CLI.

Commands:
- maestro tutorial - Show help
- maestro tutorial list - Show list of tutorials
- maestro tutorial <name|number> [page] - Show a specific tutorial page
"""
import sys
import argparse

# Tutorial content definitions
TUTORIALS = [
    {
        "name": "intro",
        "title": "Maestro Introduction",
        "pages": [
            "\nMAESTRO TUTORIAL: INTRODUCTION\n\nWelcome to Maestro! Here's how to get started with basic project management:\n\n1. PROJECT SETUP\n   - Initialize a new project: maestro init\n   - For new repositories, run: maestro repo resolve\n\n2. BASIC PROJECT MANAGEMENT\n   - Track your work with tracks, phases, and tasks\n   - View available commands:\n     * maestro track --help    # For managing project tracks\n     * maestro phase --help    # For managing project phases  \n     * maestro task --help     # For managing individual tasks\n\n3. COMMON WORKFLOW\n   - Create a track: maestro track add \"My Track Name\"\n   - Add phases to your track: maestro phase add --track <track_id> \"Phase Name\"\n   - Add tasks to phases: maestro task add --phase <phase_id> \"Task Name\"\n   - List your work: maestro task list\n   - Update task status: maestro task <task_id> complete\n   - Add verbose instructions and information about the task:\n     * maestro task set-details <task_id> steps \"1) Scan; 2) Map; 3) Verify\"\n     * maestro task set-details <task_id> context \"Scope: discovery only\"\n\n4. NEXT STEPS\n   - Explore repository structure: maestro repo hier\n   - Discuss work with AI: maestro track <id> discuss\n\nFor detailed help on any command, use --help.\n"
        ]
    },
    {
        "name": "resolve-cli",
        "title": "Converting projects to expose internals via CLI",
        "pages": [
            "\nTUTORIAL: RESOLVE-CLI (Page 1/3) - Analyze Repository\n\nGoal: Convert an existing project to expose its internals to one or more CLI programs.\n\nStep 1: Analyze Repository\nThe first step is to let Maestro understand the codebase structure and its entry points.\n\nCommands:\n  maestro repo resolve\n  maestro repo hier\n  maestro repo list\n\nMaestro will identify packages, dependencies, and potential CLI targets.\n",
            "\nTUTORIAL: RESOLVE-CLI (Page 2/3) - Create New Track\n\nStep 2: Create a track based on analysis.\nAfter analysis, you create a dedicated track for the conversion. You can visit all relevant \nfiles as tasks.\n\nCommands:\n  maestro track add \"Expose CLI for [Project Name]\"\n  maestro phase add --track <track_id> \"Discovery & Planning\"\n  maestro phase add --track <track_id> \"Implementation\"\n\nUse 'maestro task add' to map specific files or modules that need CLI exposure.\n",
            "\nTUTORIAL: RESOLVE-CLI (Page 3/3) - Implementation\n\nStep 3: Implement the created track/phases/tasks.\nIterate through the tasks, modifying the code to expose internal APIs.\n\nWorkflow:\n  maestro work any            # Find the next task\n  maestro work task <id>      # Start working on a specific task\n  # ... implement changes ...\n  maestro task <id> complete  # Mark as done\n\nUse 'maestro discuss' to get AI assistance for refactoring code to be CLI-friendly.\n"
        ]
    },
    {
        "name": "resolve-cli-for-daemon",
        "title": "Exposing internals via Daemon/Server",
        "pages": [
            "\nTUTORIAL: RESOLVE-CLI-FOR-DAEMON\n\nGoal: Handle complicated programs (e.g., GUI apps) by creating a server.\n\nIf a program is too complicated to handle as a direct CLI (e.g., GUI tied too closely to core), \nwe create a server within the GUI program and make the CLI connect to that server.\n\nWorkflow:\n1. Analyze as in 'resolve-cli'.\n2. Identify the 'Core' that needs to be exposed.\n3. Implement a lightweight server (e.g., Unix domain socket or HTTP) in the main app.\n4. Create a CLI tool that acts as a client to this server.\n5. Follow the same track/phase/task structure as 'resolve-cli'.\n"
        ]
    },
    {
        "name": "resolve-runbooks",
        "title": "Analyzing repository for runbooks",
        "pages": [
            "\nTUTORIAL: RESOLVE-RUNBOOKS\n\nGoal: Identify existing manual or semi-automated procedures in the codebase.\n\nWhat to look for:\n- Existing scripts (bash, python, etc.)\n- GUI menu items and their associated actions\n- Documentation (READMEs, Wikis) that describe procedures\n- Internal APIs that perform complex sequences\n\nCommand usage:\n  maestro runbook export    # Export identified procedures\n  maestro repo resolve      # Standard analysis helps find entry points\n\nThe 'resolve-cli' tutorial uses this information to prioritize which internals to expose.\n"
        ]
    },
    {
        "name": "resolve-runbook-workflows",
        "title": "Analyzing internal workflows for runbooks",
        "pages": [
            "\nTUTORIAL: RESOLVE-RUNBOOK-WORKFLOWS\n\nGoal: Deep dive into the logic of identified runbooks.\n\nSteps:\n1. Select a runbook (procedure).\n2. Trace its internal workflow:\n   - What APIs are called?\n   - What is the state transition?\n   - What are the user interaction points?\n\nThis information allows 'resolve-cli' to create more intelligent CLI tools that\nmimic the required internal workflows accurately.\n"
        ]
    },
    {
        "name": "work-track",
        "title": "How to work with tracks",
        "pages": [
            "\nTUTORIAL: WORK-TRACK\n\nGoal: Efficiently execute tasks within a track.\n\n1. Find next task:\n   maestro work any           # Maestro picks the best next task\n\n2. View track status:\n   maestro track list         # See all tracks\n   maestro track show <id>    # See phases and tasks in a track\n\n3. Mark task as done:\n   maestro task <id> complete\n\n4. Read task details:\n   maestro task show <id>     # Shows description and all set-details (steps, context, etc.)\n"
        ]
    },
    {
        "name": "write-track",
        "title": "How to author tracks and tasks",
        "pages": [
            "\nTUTORIAL: WRITE-TRACK\n\nGoal: Create and organize work for yourself or the AI.\n\n1. Create a track:\n   maestro track add \"Refactor Module X\"\n\n2. Create a phase:\n   maestro phase add --track <track_id> \"Cleanup\"\n\n3. Add a task with details:\n   maestro task add --phase <phase_id> \"Rename internal variables\"\n   maestro task set-details <task_id> steps \"1. Identify v_ prefix; 2. Remove prefix; 3. Run tests\"\n\n4. Edit/Rename:\n   maestro task <task_id> rename \"New Name\"\n   maestro phase <phase_id> rename \"New Phase Name\"\n"
        ]
    }
]

def add_tutorial_parser(subparsers):
    """
    Add tutorial command parser to the main argument parser.
    """
    # Create the list of tutorials for the help message
    tutorial_list = "\nAvailable Tutorials:\n"
    for i, t in enumerate(TUTORIALS, 1):
        tutorial_list += f"  {i}. {t['name']:<25}\n"
    tutorial_list += "\nRun 'maestro tutorial list' for full descriptions."

    tutorial_parser = subparsers.add_parser(
        'tutorial',
        aliases=['tut'],
        help='Interactive tutorials for Maestro features',
        description='Interactive tutorials for Maestro features.' + tutorial_list,
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    # Use positional arguments for list/name/number
    tutorial_parser.add_argument('name_or_number', nargs='?', help='Tutorial name, number, or "list"')
    tutorial_parser.add_argument('page', type=int, nargs='?', default=1, help='Page number (starting from 1)')
    
    tutorial_parser.set_defaults(func=handle_tutorial_command)


def handle_tutorial_command(args):
    """
    Handle the tutorial command.
    """
    name_or_number = getattr(args, 'name_or_number', None)
    
    if not name_or_number:
        # Show help if no arguments
        from maestro.modules.cli_parser import create_main_parser
        parser = create_main_parser(commands_to_load=['tutorial'], show_banner=False)
        parser.print_help()
        print("\nAvailable Tutorials:")
        print_tutorial_list(minimal=True)
        return

    if name_or_number in ('list', 'ls', 'l'):
        print_tutorial_list()
        return

    # Try to find the tutorial
    tutorial = None
    
    # Try as number first
    try:
        idx = int(name_or_number) - 1
        if 0 <= idx < len(TUTORIALS):
            tutorial = TUTORIALS[idx]
    except ValueError:
        # Try as name
        for t in TUTORIALS:
            if t["name"] == name_or_number:
                tutorial = t
                break
    
    if not tutorial:
        print(f"Error: Tutorial '{name_or_number}' not found.")
        print_tutorial_list()
        return

    # Show the tutorial page
    page_idx = args.page - 1
    if 0 <= page_idx < len(tutorial["pages"]):
        print(tutorial["pages"][page_idx])
        
        # Navigation hints
        if len(tutorial["pages"]) > 1:
            print(f"--- Page {args.page} of {len(tutorial['pages'])} ---")
            if args.page < len(tutorial["pages"]):
                print(f"Next page: maestro tutorial {name_or_number} {args.page + 1}")
            if args.page > 1:
                print(f"Previous page: maestro tutorial {name_or_number} {args.page - 1}")
    else:
        print(f"Error: Page {args.page} not found for tutorial '{tutorial['name']}'.")
        print(f"Tutorial '{tutorial['title']}' has {len(tutorial['pages'])} page(s).")


def print_tutorial_list(minimal=False):
    """
    Print the list of available tutorials.
    """
    if not minimal:
        print("\nAVAILABLE TUTORIALS\n")
    
    for i, t in enumerate(TUTORIALS, 1):
        if minimal:
            print(f"  {i}. {t['name']:<25}")
        else:
            print(f"{i}. {t['name']:<25} - {t['title']}")
    
    if not minimal:
        print("\nUsage: maestro tutorial <name|number> [page]")
        print("Example: maestro tutorial intro")
        print("         maestro tutorial 2 1\n")
    else:
        print("\nRun 'maestro tutorial list' for full descriptions.")