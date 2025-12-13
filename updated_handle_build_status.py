def handle_build_status(session_path, verbose=False):
    """
    Show last pipeline run results for the active build target (summary, top errors).
    """
    if verbose:
        print_debug(f"Showing build status for session: {session_path}", 2)

    # Load the session
    try:
        session = load_session(session_path)
        # Update summary file paths for backward compatibility with old sessions
        update_subtask_summary_paths(session, session_path)
    except FileNotFoundError:
        print_error(f"Session file '{session_path}' does not exist.", 2)
        sys.exit(1)
    except Exception as e:
        print_error(f"Could not load session from '{session_path}': {str(e)}", 2)
        sys.exit(1)

    # Load the active build target
    active_target = get_active_build_target(session_path)
    if not active_target:
        print_error("No active build target set. Use 'maestro build set <target>' to set an active target.", 2)
        sys.exit(1)

    print_header("BUILD STATUS")

    # Print active target information
    styled_print(f"Active Target: {active_target.name}", Colors.BRIGHT_YELLOW, Colors.BOLD, 2)
    styled_print(f"Target ID: {active_target.target_id}", Colors.BRIGHT_CYAN, None, 2)

    # Get the build directory and runs
    build_dir = get_build_dir(session_path)
    runs_dir = os.path.join(build_dir, "runs")

    if not os.path.exists(runs_dir):
        print_warning("No build runs found. Run 'maestro build run' first.", 2)
        return

    # Find the most recent run directory
    run_dirs = []
    for item in os.listdir(runs_dir):
        item_path = os.path.join(runs_dir, item)
        if os.path.isdir(item_path) and item.startswith("run_"):
            try:
                # Extract timestamp from directory name (run_timestamp)
                timestamp_str = item.split("_")[1] if "_" in item else None
                if timestamp_str and timestamp_str.isdigit():
                    run_dirs.append((int(timestamp_str), item_path))
            except:
                continue  # Skip invalid run directories

    if not run_dirs:
        print_warning("No valid build runs found in runs directory.", 2)
        return

    # Sort by timestamp to get the most recent
    run_dirs.sort(key=lambda x: x[0], reverse=True)
    latest_run_timestamp, latest_run_path = run_dirs[0]

    # Load the run summary from run.json
    run_summary_path = os.path.join(latest_run_path, "run.json")
    if not os.path.exists(run_summary_path):
        print_warning(f"Run summary not found in {latest_run_path}", 2)
        return

    with open(run_summary_path, 'r', encoding='utf-8') as f:
        run_summary = json.load(f)

    # Print run information
    styled_print(f"Last Run ID: {run_summary.get('run_id', 'unknown')}", Colors.BRIGHT_GREEN, Colors.BOLD, 2)
    styled_print(f"Run Time: {time.ctime(run_summary.get('timestamp', 0))}", Colors.BRIGHT_GREEN, None, 2)
    styled_print(f"Target: {run_summary.get('target_name', 'unknown')}", Colors.BRIGHT_CYAN, None, 2)
    styled_print(f"Success: {'Yes' if run_summary.get('success', False) else 'No'}",
                 Colors.BRIGHT_GREEN if run_summary.get('success', False) else Colors.BRIGHT_RED,
                 Colors.BOLD if run_summary.get('success', False) else Colors.BOLD, 2)
    styled_print(f"Steps: {run_summary.get('successful_steps', 0)}/{run_summary.get('step_count', 0)} succeeded", Colors.BRIGHT_CYAN, None, 2)

    # Try to load and display diagnostics from the same timestamp as the run
    diagnostics_dir = os.path.join(build_dir, "diagnostics")
    target_diagnostics_path = os.path.join(diagnostics_dir, f"{latest_run_timestamp}.json")

    if os.path.exists(target_diagnostics_path):
        with open(target_diagnostics_path, 'r', encoding='utf-8') as f:
            diagnostics_data = json.load(f)

        # Convert back to Diagnostic objects
        diagnostics = []
        for d in diagnostics_data:
            # Handle the known_issues field
            known_issues = []
            if 'known_issues' in d and d['known_issues']:
                for issue_data in d['known_issues']:
                    known_issues.append(KnownIssue(
                        id=issue_data['id'],
                        description=issue_data['description'],
                        patterns=issue_data['patterns'],
                        tags=issue_data['tags'],
                        fix_hint=issue_data['fix_hint'],
                        confidence=issue_data['confidence']
                    ))

            diagnostic = Diagnostic(
                tool=d['tool'],
                severity=d['severity'],
                file=d['file'],
                line=d['line'],
                message=d['message'],
                raw=d['raw'],
                signature=d['signature'],
                tags=d['tags'],
                known_issues=known_issues
            )
            diagnostics.append(diagnostic)

        # Group diagnostics by signature
        signature_groups = {}
        for diag in diagnostics:
            if diag.signature not in signature_groups:
                signature_groups[diag.signature] = []
            signature_groups[diag.signature].append(diag)

        print_subheader(f"DIAGNOSTICS SUMMARY ({len(diagnostics)} total)")

        # Count diagnostics by severity
        error_count = sum(1 for d in diagnostics if d.severity == 'error')
        warning_count = sum(1 for d in diagnostics if d.severity == 'warning')
        note_count = sum(1 for d in diagnostics if d.severity == 'note')

        styled_print(f"Errors: {error_count}, Warnings: {warning_count}, Notes: {note_count}", Colors.BRIGHT_YELLOW, None, 2)

        if signature_groups:
            print_subheader("TOP DIAGNOSTICS GROUPED BY SIGNATURE")

            # Sort by frequency (most common first)
            sorted_groups = sorted(
                signature_groups.items(),
                key=lambda x: len(x[1]),
                reverse=True
            )

            # Display top N diagnostic groups
            top_n = min(10, len(sorted_groups))  # Show top 10 or all if less
            for i, (signature, diag_list) in enumerate(sorted_groups[:top_n], 1):
                first_diag = diag_list[0]  # Use first diagnostic in the group for display
                count = len(diag_list)

                severity_color = Colors.BRIGHT_RED if first_diag.severity == 'error' else \
                                Colors.BRIGHT_YELLOW if first_diag.severity == 'warning' else \
                                Colors.BRIGHT_CYAN

                styled_print(f"{i:2d}. [{first_diag.severity.upper()}] x{count} - {first_diag.tool}",
                           severity_color, Colors.BOLD, 2)

                if first_diag.file or first_diag.line is not None:
                    location = f"{first_diag.file}:{first_diag.line}" if first_diag.file and first_diag.line else \
                              f"{first_diag.file}" if first_diag.file else \
                              f"line {first_diag.line}" if first_diag.line else "unknown location"
                    styled_print(f"    Location: {location}", Colors.BRIGHT_WHITE, None, 2)

                styled_print(f"    Message: {first_diag.message[:100]}{'...' if len(first_diag.message) > 100 else ''}",
                           Colors.BRIGHT_WHITE, None, 2)

                if first_diag.tags:
                    styled_print(f"    Tags: {', '.join(first_diag.tags)}", Colors.BRIGHT_MAGENTA, None, 2)

                # Show known issue information if available
                if first_diag.known_issues:
                    for issue in first_diag.known_issues:
                        confidence_str = f"({issue.confidence*100:.0f}% confidence)"
                        styled_print(f"    Known Issue {confidence_str}: {issue.description[:80]}{'...' if len(issue.description) > 80 else ''}",
                                   Colors.BRIGHT_MAGENTA, Colors.BOLD, 2)
                        styled_print(f"    Fix Hint: {issue.fix_hint[:100]}{'...' if len(issue.fix_hint) > 100 else ''}",
                                   Colors.BRIGHT_YELLOW, None, 2)

    else:
        print_warning("No diagnostics found for latest run. Run 'maestro build run' to generate diagnostics.", 2)

    # Show step results from the run summary
    print_subheader("STEP RESULTS")
    steps = run_summary.get('steps', [])
    if steps:
        for step in steps:
            step_name = step.get('step_name', 'unknown')
            success = step.get('success', False)
            exit_code = step.get('exit_code', 'unknown')

            status_color = Colors.BRIGHT_GREEN if success else Colors.BRIGHT_RED
            status_text = "SUCCESS" if success else "FAILED"

            styled_print(f"{step_name}: {status_text} (exit: {exit_code})", status_color, None, 2)
    else:
        styled_print("No step results available in run summary.", Colors.BRIGHT_YELLOW, None, 2)

    # Show last fix iteration results if available
    fix_history_path = os.path.join(build_dir, "fix_history.json")
    if os.path.exists(fix_history_path):
        with open(fix_history_path, 'r', encoding='utf-8') as f:
            fix_history = json.load(f)

        if 'iterations' in fix_history and fix_history['iterations']:
            last_iteration = fix_history['iterations'][-1]
            print_subheader("LAST FIX ITERATION")

            iter_num = last_iteration.get('iteration', 0)
            success = last_iteration.get('applied', False)
            reverted = last_iteration.get('reverted', False)

            status_color = Colors.BRIGHT_GREEN if success and not reverted else Colors.BRIGHT_RED
            status_text = "KEPT" if success and not reverted else "REVERTED" if reverted else "FAILED"
            styled_print(f"Iteration #{iter_num}: {status_text}", status_color, Colors.BOLD, 2)

            if 'target_signatures' in last_iteration:
                styled_print(f"Target Signatures: {len(last_iteration['target_signatures'])} targeted", Colors.BRIGHT_WHITE, None, 2)

            if 'verification' in last_iteration:
                verification = last_iteration['verification']
                styled_print(f"Success: {'Yes' if verification.get('success', False) else 'No'}",
                           Colors.BRIGHT_GREEN if verification.get('success', False) else Colors.BRIGHT_RED,
                           None, 2)

                if verification.get('remaining_target_signatures'):
                    styled_print(f"Signatures remaining: {len(verification['remaining_target_signatures'])}",
                               Colors.BRIGHT_RED, None, 2)

    # Always print paths for visibility
    print_subheader("BUILD ARTIFACTS")
    styled_print(f"Build runs: {runs_dir}/", Colors.BRIGHT_GREEN, None, 2)
    styled_print(f"Run {run_summary.get('run_id', 'unknown')}: {latest_run_path}/", Colors.BRIGHT_GREEN, None, 2)
    styled_print(f"Diagnostics: {diagnostics_dir}/", Colors.BRIGHT_GREEN, None, 2)
    styled_print(f"Fix history: {fix_history_path}", Colors.BRIGHT_GREEN, None, 2)