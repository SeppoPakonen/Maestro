"""Discussion templates for different session types."""

TRACK_DISCUSSION_TEMPLATE = """
# Track Discussion: {track_name}

You are discussing the "{track_name}" track.

Current status:
- Track ID: {track_id}
- Status: {status}
- Completion: {completion}%
- Phases: {phase_count}

Enter your prompt below (lines starting with # are comments):
# Type /done when finished
# Type /quit to cancel

"""

PHASE_DISCUSSION_TEMPLATE = """
# Phase Discussion: {phase_name}

You are discussing phase "{phase_name}" in track "{track_name}".

Current status:
- Phase ID: {phase_id}
- Status: {status}
- Completion: {completion}%
- Tasks: {task_count}

Enter your prompt below:
# Type /done when finished
# Type /quit to cancel

"""

GENERAL_DISCUSSION_TEMPLATE = """
# General Discussion

General AI discussion session.

Enter your prompt below:
# Type /done when finished
# Type /quit to cancel

"""