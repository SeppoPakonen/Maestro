#!/bin/bash
# Unit Test 5: AI Issue Resolution Test
# Objective: Verify AI's ability to help identify, analyze, and resolve issues

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

# USER: Create a track "Bug Fixes" and a phase "Q4 Issues"
../maestro.py track add "bug-fixes" "Bug Fixes track"
../maestro.py phase add "bug-fixes" "q4-issues" "Q4 Issues phase"

# USER: Create a problematic task or introduce an error in code
../maestro.py task add "Fix login authentication bug" --phase q4-issues --id auth-bug

# USER: Create a simple problematic file to simulate an issue
mkdir -p src
cat > src/auth.py << 'EOF'
def authenticate_user(username, password):
    # Intentional bug: this always returns True regardless of credentials
    return True  # This is the bug - should validate credentials properly

def validate_credentials(username, password):
    # This function should validate credentials against a database
    # but it's not implemented correctly
    return username == "admin" and password == "password"
EOF

# AI: Use issues command to register the issue (if available)
# If issues command is not available, we'll simulate by creating an issue file
if ../maestro.py --help | grep -q "issues"; then
    ../maestro.py issues add "Login authentication fails"
else
    echo "Issues command not available, creating issue manually"
    mkdir -p docs/issues
    cat > docs/issues/auth-failure.md << EOF
# Login authentication fails
**Status: Open**

The login authentication is not working properly. The authenticate_user function always returns True regardless of credentials.
EOF
fi

# AI: Run issues analyze command to have AI analyze the problem (if available)
if ../maestro.py --help | grep -q "issues"; then
    ../maestro.py issues analyze auth-failure
else
    echo "Analyzing the authentication issue with AI discussion"
    echo "Analyze the authentication bug in src/auth.py and suggest fixes" > analyze_issue.txt
    ../maestro.py discuss task auth-bug --mode terminal < analyze_issue.txt
fi

# AI: Use discuss command to brainstorm solutions with AI
echo "Brainstorm solutions for the authentication bug in src/auth.py" > brainstorm_solutions.txt
../maestro.py discuss task auth-bug --mode terminal < brainstorm_solutions.txt

# AI: Add solutions based on AI suggestions (if solutions command is available)
if ../maestro.py --help | grep -q "solutions"; then
    ../maestro.py solutions add "Fix the authenticate_user function to properly validate credentials"
else
    echo "Solutions command not available, documenting solution"
fi

# AI: Implement the fix using work command on the related task
# First, let's fix the bug in the source file
cat > src/auth_fixed.py << 'EOF'
def authenticate_user(username, password):
    # Fixed: Now properly validates credentials
    return validate_credentials(username, password)

def validate_credentials(username, password):
    # Fixed: Properly validate credentials against a database
    return username == "admin" and password == "password"
EOF

# AI: Use work command to implement the fix
../maestro.py work task auth-bug

# USER: Verify the issue is resolved by checking the fixed file
cat src/auth_fixed.py

# AI: Update issue status to closed (if issues command is available)
if ../maestro.py --help | grep -q "issues"; then
    ../maestro.py issues state auth-failure closed
else
    echo "Updating issue status manually"
    cat > docs/issues/auth-failure.md << EOF
# Login authentication fails
**Status: Closed**

The login authentication bug has been fixed. The authenticate_user function now properly validates credentials.
EOF
fi

# Expected Success Criteria:
# - AI correctly identifies the issue from context
# - Analysis provides meaningful insights
# - Solutions are practical and implementable
# - Fix implementation works as expected
# - Issue status updates correctly
# - No regression in other functionality