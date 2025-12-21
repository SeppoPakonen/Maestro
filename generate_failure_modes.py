#!/usr/bin/env python3
"""
Script to generate expected failure modes and error payloads using the qwen tool.
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
    success_criteria_path = "tool_event_success_criteria_final.md"
    timing_criteria_path = "input_injection_timing_success_criteria.md"
    
    protocol_content = ""
    test_plan_content = ""
    success_criteria_content = ""
    timing_criteria_content = ""
    
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
    
    try:
        with open(success_criteria_path, 'r') as f:
            success_criteria_content = f.read()
    except FileNotFoundError:
        print(f"Success criteria file {success_criteria_path} not found")
    
    try:
        with open(timing_criteria_path, 'r') as f:
            timing_criteria_content = f.read()
    except FileNotFoundError:
        print(f"Timing criteria file {timing_criteria_path} not found")
    
    # Construct a detailed prompt for failure modes and error payloads
    prompt = f"""
Based on the AI CLI Live Tool Protocol specification, the test plan, and the previously generated 
success criteria provided below, create detailed documentation identifying expected failure modes 
and error payloads as part of Task aicli4-1: Protocol Test Plan.

AI CLI Live Tool Protocol specification:
{protocol_content}

LIVE_TOOL_EVENTS_INPUT_INJECTION_TEST_PLAN.md:
{test_plan_content}

Previous tool event success criteria:
{success_criteria_content}

Input injection timing success criteria:
{timing_criteria_content}

The documentation should include:

1. Protocol-level failure modes - errors that occur at the protocol level
2. Transport-level failure modes - errors related to transport mechanisms (stdio, TCP, etc.)
3. Tool execution failure modes - errors during tool execution
4. Input injection failure modes - errors during input injection
5. Error payload structures - specific error message formats for each failure type
6. Recovery strategies - how each failure type should be handled

Focus on creating comprehensive documentation that can guide testing and implementation.
"""
    
    print("Running qwen to generate failure modes and error payloads documentation...")
    result = run_qwen_command(prompt)
    
    if result:
        output_file = "failure_modes_and_error_payloads.md"
        with open(output_file, 'w') as f:
            f.write(result)
        print(f"Failure modes and error payloads documentation generated and saved to {output_file}")
    else:
        print("Failed to generate failure modes and error payloads documentation")
        sys.exit(1)

if __name__ == "__main__":
    main()