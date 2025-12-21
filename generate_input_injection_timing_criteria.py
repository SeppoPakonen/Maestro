#!/usr/bin/env python3
"""
Script to generate success criteria for input injection timing using the qwen tool.
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
    
    protocol_content = ""
    test_plan_content = ""
    success_criteria_content = ""
    
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
    
    # Construct a detailed prompt for input injection timing success criteria
    prompt = f"""
Based on the AI CLI Live Tool Protocol specification, the test plan, and the previously generated 
tool event success criteria provided below, create detailed, specific, and measurable success 
criteria specifically for input injection timing as part of Task aicli4-1: Protocol Test Plan.

AI CLI Live Tool Protocol specification:
{protocol_content}

LIVE_TOOL_EVENTS_INPUT_INJECTION_TEST_PLAN.md:
{test_plan_content}

Previous tool event success criteria:
{success_criteria_content}

The success criteria should focus specifically on timing requirements for input injection, including:

1. Input injection response timing - how quickly injected input should be processed
2. Timing constraints during tool execution - when input can be injected during tool operations
3. Message sequencing timing - proper ordering of input injection messages
4. Flow control and backpressure timing - how input injection behaves under load
5. Session interruption timing - timing requirements for interrupt responses

Focus on creating testable, measurable criteria that are specific to input injection timing.
Each criterion should be specific enough to be validated through testing.
"""
    
    print("Running qwen to generate input injection timing success criteria...")
    result = run_qwen_command(prompt)
    
    if result:
        output_file = "input_injection_timing_success_criteria.md"
        with open(output_file, 'w') as f:
            f.write(result)
        print(f"Input injection timing success criteria generated and saved to {output_file}")
    else:
        print("Failed to generate input injection timing success criteria")
        sys.exit(1)

if __name__ == "__main__":
    main()