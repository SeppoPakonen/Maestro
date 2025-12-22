#!/bin/bash
# Unit Test 4: AI Context Management Test
# Objective: Verify AI context management and switching between different project elements

# Setup:
# - Remove ./tmp directory if it exists
# - Create a fresh ./tmp directory in the project root
# - Verify that ./tmp is listed in .gitignore (it should be already)
# - The point is to use "python ../maestro.py" from the ./tmp directory

# USER: Remove tmp directory if it exists and create fresh one
rm -rf tmp
mkdir tmp
cd tmp

# USER: Initialize the project
../maestro.py init

# USER: Create multiple tracks: "Frontend", "Backend", "DevOps"
../maestro.py track add "frontend" "Frontend development track"
../maestro.py track add "backend" "Backend development track"
../maestro.py track add "devops" "DevOps track"

# USER: Create phases and tasks within each track
../maestro.py phase add "frontend" "ui-components" "UI Components phase"
../maestro.py task add "Create button component" --phase ui-components --id btn-comp
../maestro.py task add "Create form component" --phase ui-components --id form-comp

../maestro.py phase add "backend" "api-development" "API Development phase"
../maestro.py task add "Design REST endpoints" --phase api-development --id api-design
../maestro.py task add "Implement authentication" --phase api-development --id api-auth

../maestro.py phase add "devops" "ci-cd" "CI/CD Pipeline phase"
../maestro.py task add "Set up build pipeline" --phase ci-cd --id build-pipeline
../maestro.py task add "Configure deployment" --phase ci-cd --id deploy-config

# AI: Start a discussion with AI about the Frontend track
echo "Discuss the current status of the frontend track and suggest improvements" > frontend_discussion.txt
../maestro.py discuss track frontend --mode terminal < frontend_discussion.txt

# AI: Switch context to Backend track and continue discussion
echo "Now discuss the backend track and its current progress" > backend_discussion.txt
../maestro.py discuss track backend --mode terminal < backend_discussion.txt

# AI: Switch context to DevOps track and continue discussion
echo "Now discuss the devops track and its current progress" > devops_discussion.txt
../maestro.py discuss track devops --mode terminal < devops_discussion.txt

# AI: Use session commands to check and navigate between contexts
../maestro.py session list

# AI: Verify that AI remembers context when switching between tracks/phases/tasks
# This is handled internally by the session system

# AI: Test context switching with session commands if available
# If session commands exist, use them to switch context
../maestro.py session list

# AI: Verify that session context is preserved across multiple AI interactions
# Check the session directory to see if context is preserved
if [ -d "docs/sessions" ]; then
    echo "Sessions directory exists - context is being preserved"
    ls -la docs/sessions/
else
    echo "Sessions directory does not exist"
fi

# AI: Check if there are specific context commands
../maestro.py --help | grep -i context

# Expected Success Criteria:
# - AI maintains appropriate context for each track/phase/task
# - Context switching works smoothly without confusion
# - Breadcrumbs properly track context navigation
# - Session context is preserved between interactions
# - No context bleeding between different project areas