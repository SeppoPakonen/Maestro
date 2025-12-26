# Command: solutions

## Overview
The `solutions` command manages solution rules that can be automatically matched to issues, including build errors. This system provides a rule-based approach to quickly resolve common problems without requiring manual intervention or deep AI analysis.

## Solution Rule Structure
A "Solution rule" consists of:
- **title**: Human-readable name for the solution
- **problem**: Description of the problem the solution addresses
- **steps**: List of actions to apply the solution
- **keywords**: Keywords that trigger matching when present in issue text
- **regex**: Regular expressions that trigger matching when they match issue text
- **contexts**: Context tags (file type, tool, etc.) that influence matching
- **confidence**: Confidence level (0-100) of solution effectiveness
- **success_rate**: Historical success rate of the solution

## Storage Location
- **Project solutions**: Stored in `docs/solutions/` directory within the project
- **External solutions**: Stored in `~/.maestro/repos.json` referenced repositories under `docs/solutions/`

## Matching Algorithm
The matching algorithm works as follows:
1. **Keyword matching**: Each keyword in the solution is searched for in the issue text (case-insensitive)
2. **Regex matching**: Each regex pattern is applied to the issue text (case-insensitive)
3. **Context matching**: Solution contexts are compared with issue contexts (file extension, tool, etc.)
4. **Scoring**: Each match contributes to a score:
   - Keyword match: +10 points
   - Regex match: +15 points
   - Context match: +8 points
   - Problem text match: +5 points
5. **Confidence weighting**: The raw score is weighted with the solution's confidence value
6. **Results**: Solutions with scores > 0 are returned, sorted by score

## Translation to Issues/Tasks
When a solution matches an issue:
- The solution ID is recorded in the issue's metadata
- The solution can be referenced during issue processing
- The solution's steps can be applied automatically if appropriate

## Dependencies and Prioritization
- Solutions are applied based on their match score
- Higher scoring solutions take precedence
- No explicit dependency system between solutions exists

## Failure Semantics
- **Malformed rule definitions**: Invalid regex patterns are skipped during matching
- **Ambiguous matches**: All matching solutions are returned; highest scoring is prioritized
- **Solution action fails**: The failure doesn't prevent other workflow steps; a fallback process continues

## Not Covered
This documentation covers using existing solutions for matching against issues. It does not cover:
- Editing solution rules (covered in a separate workflow)
- Creating new solution rules (covered in a separate workflow)
- The UI/UX aspects of solution management beyond CLI commands

## Commands
- `maestro solutions list`: List all available solutions
- `maestro solutions add`: Add a new solution rule
- `maestro solutions show <id>`: Display details of a specific solution
- `maestro solutions remove <id>`: Remove a solution rule
- `maestro solutions edit <id>`: Edit a solution in your $EDITOR