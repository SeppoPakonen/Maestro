#!/bin/bash
# Unit Test 3: AI Planning Test
# Objective: Verify AI planning capabilities with track/phase/task creation

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

# USER: Create a main track for "Website Redesign" project
../maestro.py track add "website-redesign" "Website Redesign Project"

# AI: Use AI to plan phases for the project by running discuss command and asking AI to suggest phases
# We'll use the discuss command to get AI suggestions for phases
echo "Suggest 4-5 phases for a Website Redesign project with brief descriptions" > ai_plan_prompt.txt
../maestro.py discuss track website-redesign --mode terminal < ai_plan_prompt.txt

# USER: Based on AI's suggestions, create 4-5 phases: "Research", "Design", "Development", "Testing", "Deployment"
../maestro.py phase add "website-redesign" "research" "Research phase for the website redesign"
../maestro.py phase add "website-redesign" "design" "Design phase for the website redesign"
../maestro.py phase add "website-redesign" "development" "Development phase for the website redesign"
../maestro.py phase add "website-redesign" "testing" "Testing phase for the website redesign"
../maestro.py phase add "website-redesign" "deployment" "Deployment phase for the website redesign"

# AI: For each phase, create 2-3 tasks using AI suggestions
# We'll use discuss command for each phase to get task suggestions
echo "Suggest 2-3 tasks for the research phase of website redesign" > ai_research_prompt.txt
../maestro.py discuss phase research --mode terminal < ai_research_prompt.txt

# USER: Create tasks for research phase based on AI suggestions
../maestro.py task add "Research user requirements" --phase research --id research-req
../maestro.py task add "Analyze competitor websites" --phase research --id research-comp
../maestro.py task add "Survey current users" --phase research --id research-survey

# USER: Create tasks for design phase based on AI suggestions
echo "Suggest 2-3 tasks for the design phase of website redesign" > ai_design_prompt.txt
../maestro.py discuss phase design --mode terminal < ai_design_prompt.txt
../maestro.py task add "Create wireframes" --phase design --id design-wireframes
../maestro.py task add "Design UI components" --phase design --id design-ui
../maestro.py task add "Create style guide" --phase design --id design-style

# USER: Create tasks for development phase based on AI suggestions
echo "Suggest 2-3 tasks for the development phase of website redesign" > ai_dev_prompt.txt
../maestro.py discuss phase development --mode terminal < ai_dev_prompt.txt
../maestro.py task add "Set up development environment" --phase development --id dev-setup
../maestro.py task add "Implement frontend components" --phase development --id dev-frontend
../maestro.py task add "Implement backend functionality" --phase development --id dev-backend

# USER: Create tasks for testing phase based on AI suggestions
echo "Suggest 2-3 tasks for the testing phase of website redesign" > ai_test_prompt.txt
../maestro.py discuss phase testing --mode terminal < ai_test_prompt.txt
../maestro.py task add "Write unit tests" --phase testing --id test-unit
../maestro.py task add "Perform integration testing" --phase testing --id test-integration
../maestro.py task add "User acceptance testing" --phase testing --id test-acceptance

# USER: Create tasks for deployment phase based on AI suggestions
echo "Suggest 2-3 tasks for the deployment phase of website redesign" > ai_deploy_prompt.txt
../maestro.py discuss phase deployment --mode terminal < ai_deploy_prompt.txt
../maestro.py task add "Prepare production environment" --phase deployment --id deploy-env
../maestro.py task add "Deploy website" --phase deployment --id deploy-website
../maestro.py task add "Post-deployment monitoring" --phase deployment --id deploy-monitor

# AI: Verify that the plan is properly structured with tracks, phases, and tasks
../maestro.py track list
../maestro.py phase list
../maestro.py task list

# AI: Use `python ../maestro.py plan tree` to visualize the plan hierarchy
../maestro.py plan tree

# AI: Mark early tasks as done and verify progress tracking
../maestro.py task complete research-req
../maestro.py task complete research-comp

# AI: Check that tasks are marked as done
../maestro.py task list

# Expected Success Criteria:
# - AI provides meaningful phase suggestions
# - All phases and tasks are created successfully
# - Plan tree shows proper hierarchy
# - Progress tracking works correctly
# - No errors during creation process