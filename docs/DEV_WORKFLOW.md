# Development Workflow for Maestro

This document outlines the shared development workflow to reduce conflicts and improve collaboration in the Maestro project.

## Branch Naming Convention

Use descriptive, consistent branch names following this pattern:

```
<type>/<scope>/<description>
```

### Types
- `feat`: New features
- `fix`: Bug fixes
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic changes)
- `refactor`: Code refactoring (no new features or bug fixes)
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

### Examples
- `feat/cli-commands-add-validation`
- `fix/repo-resolve-null-pointer`
- `docs/feature-matrix-update`
- `chore/cleanup-unused-imports`

## Git Workflow

### Commit Guidelines
- Make small, focused commits with clear, descriptive messages
- Each commit should represent a complete, logical change
- Use present tense, imperative mood in commit messages
- Example: "docs: add shared-repo workflow guardrails" not "docs: adding shared-repo workflow guardrails"

### Rebase Policy
- Always rebase your branch on the latest main before creating a pull request
- Use `git fetch` and `git rebase origin/main` to keep your branch up-to-date
- Resolve conflicts locally before pushing to avoid messy merge commits
- If you've already pushed your branch, you may need to force push (`git push --force-with-lease`) after rebasing

## Collaboration Guidelines

### CLI vs TUI Development
- **CLI-only threads**: When working on CLI-only features, avoid touching TUI-related paths:
  - Don't modify TUI-specific files (typically in `tui/` directories if they exist)
  - Don't change TUI dependencies or configuration
  - Don't modify shared UI components unless absolutely necessary

### Conflict Prevention
- Always pull latest changes before starting work
- Communicate with team members about areas you're modifying
- Keep branches short-lived (finish work and merge within 1-2 days when possible)

## Git Hygiene
- Keep your working directory clean
- Use `.gitignore` appropriately for temporary files
- Regularly clean up old branches that have been merged
- Run tests locally before pushing to avoid breaking the CI

## Code Review Process
- Submit small pull requests when possible
- Ensure all tests pass before requesting review
- Provide context in PR descriptions
- Be responsive to review comments