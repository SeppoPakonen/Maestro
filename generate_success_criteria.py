#!/usr/bin/env python3
"""
Script to generate success criteria for tool event capture using the qwen tool.
"""
import subprocess
import json
import sys
import os

def run_qwen_command(prompt):
    """Run a qwen command with the given prompt and return the output."""
    try:
        result = subprocess.run([
            os.path.expanduser("~/node_modules/.bin/qwen"), 
            "-y", 
            prompt
        ], capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            return result.stdout
        else:
            print(f"Error running qwen command: {result.stderr}")
            return None
    except subprocess.TimeoutExpired:
        print("Qwen command timed out")
        return None
    except Exception as e:
        print(f"Error running qwen command: {e}")
        return None

def main():
    # Read the relevant documentation files
    protocol_doc_path = "AI_CLI_LIVE_TOOL_PROTOCOL.md"
    test_plan_path = "LIVE_TOOL_EVENTS_INPUT_INJECTION_TEST_PLAN.md"
    
    protocol_content = ""
    test_plan_content = ""
    
    try:
        with open(protocol_doc_path, 'r') as f:
            protocol_content = f.read()
    except FileNotFoundError:
        print(f"Protocol documentation file {protocol_doc_path} not found")
    
    try:
        with open(test_plan_path, 'r') as f:
            test_plan_content = f.read()
    except FileNotFoundError:
        print(f"Test plan file {test_plan_path} not found")
    
    # Construct a detailed prompt
    prompt = f"""
Based on the AI CLI Live Tool Protocol specification and the test plan provided below,
create detailed, specific, and measurable success criteria for tool event capture as part of Task aicli4-1: Protocol Test Plan.

AI CLI Live Tool Protocol specification:
{protocol_content}

LIVE_TOOL_EVENTS_INPUT_INJECTION_TEST_PLAN.md:
{test_plan_content}

The success criteria should be structured as a document with the following sections:
1. Message Types Validation - specific criteria for validating each message type
2. Content Accuracy Requirements - specific requirements for content accuracy
3. Timing Requirements - specific timing constraints and expectations
4. Correlation Validation - specific requirements for correlation between events

Focus on creating testable, measurable criteria that can be used to validate
whether tool events are captured correctly in the AI CLI Live Tool Protocol.
Each criterion should be specific enough to be validated through testing.
"""
    
    print("Running qwen to generate success criteria...")
    result = run_qwen_command(prompt)
    
    if result:
        output_file = "tool_event_success_criteria_final.md"
        with open(output_file, 'w') as f:
            f.write(result)
        print(f"Success criteria generated and saved to {output_file}")
        
        # Also update the phase documentation
        update_phase_docs()
    else:
        print("Failed to generate success criteria")
        sys.exit(1)

def update_phase_docs():
    """Update the phase documentation to mark the task as completed."""
    # This would update the phase docs but for now we'll just print a message
    print("Would update phase documentation to reflect progress on aicli4-1")

if __name__ == "__main__":
    main()